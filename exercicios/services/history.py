from __future__ import annotations

from dataclasses import dataclass

from ..models import ExercicioCatalogo
from procedimentos.models import Procedimento, Sessao


STATUS_NORMAL = "normal"
STATUS_RED = "red"
STATUS_BLUE = "blue"


@dataclass(frozen=True)
class ExerciseHistoryStatus:
    exercise_id: int
    state: str
    badge_class: str
    border_class: str
    label: str
    tooltip: str
    warning: bool
    warning_message: str
    used_in_previous_session: bool
    consecutive_usage_count: int
    projected_consecutive_usage_count: int
    sessions_since_last_use: int | None
    in_cooldown: bool


class SessionExerciseHistoryService:
    """Calcula status visual e histórico de exercícios por sessão."""

    COUNTABLE_SESSION_STATUSES = {
        Sessao.STATUS_AGENDADA,
        Sessao.STATUS_REALIZADA,
    }

    def __init__(self, procedimento: Procedimento):
        self.procedimento = procedimento
        self.sessions = [
            sessao
            for sessao in procedimento.sessoes.all()
            if sessao.is_active and sessao.status in self.COUNTABLE_SESSION_STATUSES
        ]
        self.sessions.sort(
            key=lambda sessao: (
                sessao.data_hora,
                sessao.numero if sessao.numero is not None else 999999,
                sessao.pk,
            )
        )
        self.session_index = {sessao.pk: index for index, sessao in enumerate(self.sessions)}
        self.legacy_items = [item for item in procedimento.procedimento_exercicios.all() if item.is_active]
        self.legacy_ids = {item.exercicio_id for item in self.legacy_items}
        self.legacy_by_exercicio_id = {item.exercicio_id: item for item in self.legacy_items}
        self.exercise_ids_by_session = {sessao.pk: self.get_selected_ids_for_session(sessao)[0] for sessao in self.sessions}

    def get_selected_ids_for_session(self, sessao: Sessao) -> tuple[set[int], str]:
        explicit_ids = {item.exercicio_id for item in sessao.sessao_exercicios.all() if item.is_active}
        if explicit_ids:
            return explicit_ids, "sessao"
        return set(self.legacy_ids), "procedimento"

    def get_selection_source_for_session(self, sessao: Sessao) -> str:
        return self.get_selected_ids_for_session(sessao)[1]

    def get_exercise_status_for_session(
        self,
        sessao: Sessao,
        exercicio: ExercicioCatalogo,
        *,
        selected_in_current: bool | None = None,
    ) -> ExerciseHistoryStatus:
        session_position = self.session_index.get(sessao.pk)
        if session_position is None:
            return self._build_default_status(exercicio)

        current_exercises = self.exercise_ids_by_session.get(sessao.pk, set())
        is_selected = exercicio.pk in current_exercises if selected_in_current is None else selected_in_current

        last_used_position = None
        for index in range(session_position - 1, -1, -1):
            previous_session = self.sessions[index]
            if exercicio.pk in self.exercise_ids_by_session.get(previous_session.pk, set()):
                last_used_position = index
                break

        sessions_since_last_use = None
        used_in_previous_session = False
        prior_consecutive_usage_count = 0
        if last_used_position is not None:
            sessions_since_last_use = session_position - last_used_position
            used_in_previous_session = sessions_since_last_use == 1
            prior_consecutive_usage_count = self._count_streak_ending_at(last_used_position, exercicio.pk)

        consecutive_usage_count = self._count_streak_ending_at(session_position, exercicio.pk) if is_selected else 0
        projected_consecutive_usage_count = prior_consecutive_usage_count + 1 if used_in_previous_session else 1
        if is_selected:
            projected_consecutive_usage_count = consecutive_usage_count or projected_consecutive_usage_count

        cooldown_window = exercicio.sessoes_ate_cooldown
        in_cooldown = (
            sessions_since_last_use is not None
            and cooldown_window > 0
            and sessions_since_last_use <= cooldown_window
        )

        if used_in_previous_session or consecutive_usage_count > 1:
            state = STATUS_RED
            label = "Já realizado na sessão anterior"
            tooltip = "Exercício já utilizado na sessão imediatamente anterior."
        elif in_cooldown:
            state = STATUS_BLUE
            label = "Em período de cooldown"
            tooltip = f"Exercício utilizado há {sessions_since_last_use} sessão(ões), ainda dentro do período recente."
        else:
            state = STATUS_NORMAL
            label = "Disponível"
            tooltip = "Exercício sem uso recente para esta sessão."

        warning_limit = exercicio.max_sessoes_consecutivas
        warning = warning_limit > 0 and projected_consecutive_usage_count >= warning_limit
        warning_message = ""
        if warning:
            warning_message = (
                f"O exercício {exercicio.nome} já foi realizado por "
                f"{projected_consecutive_usage_count} sessões consecutivas."
            )

        badge_class, border_class = self._style_for_state(state)
        return ExerciseHistoryStatus(
            exercise_id=exercicio.pk,
            state=state,
            badge_class=badge_class,
            border_class=border_class,
            label=label,
            tooltip=tooltip,
            warning=warning,
            warning_message=warning_message,
            used_in_previous_session=used_in_previous_session,
            consecutive_usage_count=consecutive_usage_count,
            projected_consecutive_usage_count=projected_consecutive_usage_count,
            sessions_since_last_use=sessions_since_last_use,
            in_cooldown=in_cooldown,
        )

    def get_status_map_for_session(
        self,
        sessao: Sessao,
        exercicios: list[ExercicioCatalogo],
    ) -> dict[int, ExerciseHistoryStatus]:
        return {exercicio.pk: self.get_exercise_status_for_session(sessao, exercicio) for exercicio in exercicios}

    def get_assigned_items_for_session(self, sessao: Sessao) -> list[dict]:
        explicit_items = [item for item in sessao.sessao_exercicios.all() if item.is_active]
        source_items = explicit_items or self.legacy_items
        assigned_items = []
        for fallback_order, item in enumerate(source_items, start=1):
            status = self.get_exercise_status_for_session(sessao, item.exercicio, selected_in_current=True)
            assigned_items.append(
                {
                    "item": item,
                    "status": status,
                    "is_legacy": not explicit_items,
                    "ordem_exibicao": item.ordem or fallback_order,
                }
            )
        assigned_items.sort(key=lambda item: (item["ordem_exibicao"], item["item"].pk))
        return assigned_items

    def _count_streak_ending_at(self, session_position: int, exercise_id: int) -> int:
        streak = 0
        for index in range(session_position, -1, -1):
            session = self.sessions[index]
            if exercise_id not in self.exercise_ids_by_session.get(session.pk, set()):
                break
            streak += 1
        return streak

    def _build_default_status(self, exercicio: ExercicioCatalogo) -> ExerciseHistoryStatus:
        badge_class, border_class = self._style_for_state(STATUS_NORMAL)
        return ExerciseHistoryStatus(
            exercise_id=exercicio.pk,
            state=STATUS_NORMAL,
            badge_class=badge_class,
            border_class=border_class,
            label="Disponível",
            tooltip="Exercício sem uso recente para esta sessão.",
            warning=False,
            warning_message="",
            used_in_previous_session=False,
            consecutive_usage_count=0,
            projected_consecutive_usage_count=1,
            sessions_since_last_use=None,
            in_cooldown=False,
        )

    @staticmethod
    def _style_for_state(state: str) -> tuple[str, str]:
        if state == STATUS_RED:
            return ("badge text-bg-danger", "exercise-item-red")
        if state == STATUS_BLUE:
            return ("badge text-bg-primary", "exercise-item-blue")
        return ("badge bg-light text-dark border", "exercise-item-normal")

