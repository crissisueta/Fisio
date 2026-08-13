from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from pacientes.models import Paciente
from procedimentos.models import Procedimento, Sessao
from procedimentos.services.scheduling import (
    create_session_for_procedimento,
    find_schedule_conflict,
)
from ..models import ExercicioCatalogo, ProcedimentoExercicio, SessaoExercicio


COLOR_RED = "red"
COLOR_BLUE = "blue"
COLOR_BLACK = "black"
DAY_PAST = "past"
DAY_TODAY = "today"
DAY_FUTURE = "future"
GRID_SESSION_STATUSES = {
    Sessao.STATUS_AGENDADA,
    Sessao.STATUS_REALIZADA,
}
COMPLETED_SESSION_STATUSES = {
    Sessao.STATUS_REALIZADA,
}
TRACKING_SESSION_OBSERVATION = "Criada pelo controle mensal de exercícios."


@dataclass(frozen=True)
class MonthlyTrackingDay:
    day: int
    date: date
    temporal_state: str


@dataclass(frozen=True)
class MonthlyExerciseDay:
    day: int
    date: date
    marked: bool
    temporal_state: str

    @property
    def performed(self) -> bool:
        return self.marked


@dataclass(frozen=True)
class MonthlyExerciseRow:
    exercise_id: int
    name: str
    color_state: str
    days: list[MonthlyExerciseDay]
    last_performed: date | None
    performed_in_last_session: bool


@dataclass(frozen=True)
class MonthlyExerciseGroup:
    category_id: int | None
    category_name: str
    exercises: list[MonthlyExerciseRow]


@dataclass(frozen=True)
class MonthlyExerciseTrackingTable:
    patient_id: int
    month: date
    month_param: str
    month_label: str
    previous_month_param: str
    next_month_param: str
    days: list[MonthlyTrackingDay]
    groups: list[MonthlyExerciseGroup]
    last_session_id: int | None


@dataclass(frozen=True)
class MarkExerciseDayResult:
    sessao: Sessao
    sessao_exercicio: SessaoExercicio
    created_session: bool
    created_link: bool
    target_date: date


@dataclass(frozen=True)
class UnmarkExerciseDayResult:
    sessao_id: int
    exercise_id: int
    deleted_session: bool
    target_date: date


def parse_month_reference(month_value: str | date | None) -> date:
    if isinstance(month_value, date):
        return month_value.replace(day=1)

    if month_value:
        try:
            year_text, month_text = month_value.split("-", 1)
            return date(int(year_text), int(month_text), 1)
        except (TypeError, ValueError):
            pass

    return timezone.localdate().replace(day=1)


def build_monthly_exercise_tracking_table(
    paciente: Paciente,
    month: str | date | None = None,
) -> MonthlyExerciseTrackingTable:
    """Build a patient-scoped monthly exercise table.

    The exercise universe is intentionally the union of active
    ProcedimentoExercicio rows and active SessaoExercicio rows for this patient.
    That keeps prescribed exercises visible before they are executed and keeps
    exercises introduced directly in a session visible afterward.
    """

    month_start = parse_month_reference(month)
    month_end = _next_month(month_start)
    month_start_datetime = _aware_month_boundary(month_start)
    month_end_datetime = _aware_month_boundary(month_end)
    _, month_day_count = calendar.monthrange(month_start.year, month_start.month)
    today = timezone.localdate()
    month_days = [
        MonthlyTrackingDay(
            day=day,
            date=date(month_start.year, month_start.month, day),
            temporal_state=_get_day_temporal_state(date(month_start.year, month_start.month, day), today),
        )
        for day in range(1, month_day_count + 1)
    ]

    last_session = (
        Sessao.objects.filter(
            procedimento__paciente=paciente,
            status=Sessao.STATUS_REALIZADA,
        )
        .order_by("-data_hora")
        .first()
    )

    last_session_exercise_ids = _get_last_session_exercise_ids(last_session)
    marked_dates_by_exercise = _get_session_exercise_dates_by_statuses(
        paciente,
        statuses=GRID_SESSION_STATUSES,
        start_datetime=month_start_datetime,
        end_datetime=month_end_datetime,
    )
    last_performed_by_exercise = _get_last_performed_dates_by_exercise(paciente)
    exercise_universe = _get_exercise_universe(paciente)

    grouped_rows: dict[tuple[str, int | None], list[MonthlyExerciseRow]] = {}
    for exercise_data in sorted(exercise_universe.values(), key=_exercise_display_order):
        exercise_id = exercise_data["exercise_id"]
        marked_dates = marked_dates_by_exercise.get(exercise_id, set())
        last_performed = last_performed_by_exercise.get(exercise_id)
        performed_in_last_session = exercise_id in last_session_exercise_ids
        color_state = _get_color_state(
            performed_in_last_session=performed_in_last_session,
            last_performed=last_performed,
            today=today,
        )
        row = MonthlyExerciseRow(
            exercise_id=exercise_id,
            name=exercise_data["name"],
            color_state=color_state,
            days=[
                MonthlyExerciseDay(
                    day=month_day.day,
                    date=month_day.date,
                    marked=month_day.date in marked_dates,
                    temporal_state=month_day.temporal_state,
                )
                for month_day in month_days
            ],
            last_performed=last_performed,
            performed_in_last_session=performed_in_last_session,
        )
        group_key = (exercise_data["category_name"], exercise_data["category_id"])
        grouped_rows.setdefault(group_key, []).append(row)

    groups = [
        MonthlyExerciseGroup(category_id=category_id, category_name=category_name, exercises=rows)
        for (category_name, category_id), rows in grouped_rows.items()
    ]

    return MonthlyExerciseTrackingTable(
        patient_id=paciente.pk,
        month=month_start,
        month_param=_month_param(month_start),
        month_label=month_start.strftime("%m/%Y"),
        previous_month_param=_month_param(_previous_month(month_start)),
        next_month_param=_month_param(month_end),
        days=month_days,
        groups=groups,
        last_session_id=last_session.pk if last_session else None,
    )


@transaction.atomic
def mark_exercise_day_for_patient(
    paciente: Paciente,
    *,
    exercise_id: int,
    target_date: date,
) -> MarkExerciseDayResult:
    """Mark a patient exercise on a calendar day.

    The exercise row must already belong to the patient's monthly table
    universe: active ProcedimentoExercicio rows plus active SessaoExercicio
    rows. This keeps the write path tied to the same patient/procedure context
    used by the read model instead of creating unrelated exercise dashboards.
    """

    exercicio = ExercicioCatalogo.objects.select_related("categoria").get(pk=exercise_id)
    procedimento = _get_tracking_procedure_for_exercise(paciente, exercicio)
    procedimento_exercicio = _ensure_procedure_exercise(procedimento, exercicio)
    session_status = _session_status_for_marked_date(target_date)
    sessao, created_session = _get_or_create_session_for_date(procedimento, target_date, session_status)
    sessao_exercicio, created_link = _get_or_create_session_exercise(
        sessao,
        procedimento_exercicio,
        session_status,
    )

    return MarkExerciseDayResult(
        sessao=sessao,
        sessao_exercicio=sessao_exercicio,
        created_session=created_session,
        created_link=created_link,
        target_date=target_date,
    )


@transaction.atomic
def unmark_exercise_day_for_patient(
    paciente: Paciente,
    *,
    exercise_id: int,
    target_date: date,
) -> UnmarkExerciseDayResult:
    """Remove a patient exercise mark from a calendar day."""

    exercicio = ExercicioCatalogo.objects.select_related("categoria").get(pk=exercise_id)
    sessao_exercicio = _get_explicit_session_exercise_for_date(paciente, exercicio, target_date)
    if sessao_exercicio:
        return _unmark_explicit_session_exercise(sessao_exercicio, target_date)

    fallback_session = _get_fallback_session_for_date(paciente, exercicio, target_date)
    if fallback_session is None:
        raise ValidationError("Nenhum exercício marcado foi encontrado para este dia.")

    materialized_count = _materialize_session_exercises_except(fallback_session, exercicio)
    if materialized_count:
        return UnmarkExerciseDayResult(
            sessao_id=fallback_session.pk,
            exercise_id=exercise_id,
            deleted_session=False,
            target_date=target_date,
        )

    if _is_tracking_created_session(fallback_session):
        sessao_id = fallback_session.pk
        fallback_session.delete()
        return UnmarkExerciseDayResult(
            sessao_id=sessao_id,
            exercise_id=exercise_id,
            deleted_session=True,
            target_date=target_date,
        )

    raise ValidationError("Não foi possível desmarcar este exercício sem remover a sessão.")


def _get_last_session_exercise_ids(last_session: Sessao | None) -> set[int]:
    if last_session is None:
        return set()

    return set(
        SessaoExercicio.all_objects.filter(
            is_active=True,
            sessao=last_session,
        ).values_list("exercicio_id", flat=True)
    )


def _get_session_exercise_dates_by_statuses(
    paciente: Paciente,
    *,
    statuses: set[str],
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
) -> dict[int, set[date]]:
    current_timezone = timezone.get_current_timezone()
    explicit_queryset = _session_exercises_queryset_for_statuses(paciente, statuses)
    fallback_sessions_queryset = _sessions_without_explicit_exercises_queryset(paciente, statuses)

    if start_datetime is not None:
        explicit_queryset = explicit_queryset.filter(sessao__data_hora__gte=start_datetime)
        fallback_sessions_queryset = fallback_sessions_queryset.filter(data_hora__gte=start_datetime)
    if end_datetime is not None:
        explicit_queryset = explicit_queryset.filter(sessao__data_hora__lt=end_datetime)
        fallback_sessions_queryset = fallback_sessions_queryset.filter(data_hora__lt=end_datetime)

    explicit_rows = (
        explicit_queryset
        .annotate(performed_date=TruncDate("sessao__data_hora", tzinfo=current_timezone))
        .values_list("exercicio_id", "performed_date")
        .distinct()
    )

    dates_by_exercise: dict[int, set[date]] = {}
    for exercise_id, performed_date in explicit_rows:
        dates_by_exercise.setdefault(exercise_id, set()).add(performed_date)

    fallback_dates_by_procedure: dict[int, set[date]] = {}
    fallback_sessions = (
        fallback_sessions_queryset
        .annotate(performed_date=TruncDate("data_hora", tzinfo=current_timezone))
        .values_list("procedimento_id", "performed_date")
        .distinct()
    )
    for procedimento_id, performed_date in fallback_sessions:
        fallback_dates_by_procedure.setdefault(procedimento_id, set()).add(performed_date)

    if not fallback_dates_by_procedure:
        return dates_by_exercise

    procedure_exercise_rows = (
        ProcedimentoExercicio.all_objects.filter(
            is_active=True,
            procedimento_id__in=fallback_dates_by_procedure.keys(),
            procedimento__is_active=True,
            procedimento__paciente=paciente,
            procedimento__paciente__is_active=True,
            procedimento__tipo_procedimento__is_active=True,
        )
        .values_list("procedimento_id", "exercicio_id")
        .distinct()
    )
    for procedimento_id, exercise_id in procedure_exercise_rows:
        dates_by_exercise.setdefault(exercise_id, set()).update(fallback_dates_by_procedure[procedimento_id])

    return dates_by_exercise


def _get_tracking_procedure_for_exercise(paciente: Paciente, exercicio: ExercicioCatalogo) -> Procedimento:
    procedimento_exercicio = (
        ProcedimentoExercicio.objects.select_related("procedimento")
        .filter(
            procedimento__paciente=paciente,
            exercicio=exercicio,
        )
        .order_by("-procedimento__created_at", "-created_at", "-procedimento_id")
        .first()
    )
    if procedimento_exercicio:
        return procedimento_exercicio.procedimento

    sessao_exercicio = (
        SessaoExercicio.objects.select_related("sessao__procedimento")
        .filter(
            sessao__procedimento__paciente=paciente,
            exercicio=exercicio,
        )
        .order_by("-sessao__data_hora", "-created_at", "-sessao__procedimento_id")
        .first()
    )
    if sessao_exercicio:
        return sessao_exercicio.sessao.procedimento

    raise ValidationError("Este exercício não está vinculado a um procedimento ativo deste paciente.")


def _ensure_procedure_exercise(procedimento: Procedimento, exercicio: ExercicioCatalogo) -> ProcedimentoExercicio:
    existing = (
        ProcedimentoExercicio.all_objects.filter(
            procedimento=procedimento,
            exercicio=exercicio,
        )
        .order_by("-is_active", "created_at", "pk")
        .first()
    )
    if existing is None:
        return ProcedimentoExercicio.objects.create(procedimento=procedimento, exercicio=exercicio)

    if not existing.is_active:
        existing.restore()
    return existing


def _get_or_create_session_for_date(
    procedimento: Procedimento,
    target_date: date,
    desired_status: str,
) -> tuple[Sessao, bool]:
    start_datetime = _aware_month_boundary(target_date)
    end_datetime = timezone.make_aware(
        datetime.combine(target_date, time.max),
        timezone.get_current_timezone(),
    )
    sessao = (
        Sessao.objects.filter(
            procedimento=procedimento,
            data_hora__gte=start_datetime,
            data_hora__lte=end_datetime,
        )
        .order_by("data_hora", "pk")
        .first()
    )

    if sessao:
        _sync_session_status_for_mark(sessao, desired_status)
        return sessao, False

    sessao = create_session_for_procedimento(
        procedimento,
        data_hora=_default_session_datetime_for_date(target_date),
        duracao_minutos=60,
        status=desired_status,
        observacoes=TRACKING_SESSION_OBSERVATION,
    )
    return sessao, True


def _unmark_explicit_session_exercise(
    sessao_exercicio: SessaoExercicio,
    target_date: date,
) -> UnmarkExerciseDayResult:
    sessao = sessao_exercicio.sessao
    sessao_id = sessao.pk
    exercise_id = sessao_exercicio.exercicio_id
    active_other_count = (
        SessaoExercicio.objects.filter(sessao=sessao, is_active=True)
        .exclude(pk=sessao_exercicio.pk)
        .count()
    )

    if active_other_count == 0 and _is_tracking_created_session(sessao):
        sessao_exercicio.delete()
        sessao.delete()
        return UnmarkExerciseDayResult(
            sessao_id=sessao_id,
            exercise_id=exercise_id,
            deleted_session=True,
            target_date=target_date,
        )

    if active_other_count == 0:
        materialized_count = _materialize_session_exercises_except(sessao, sessao_exercicio.exercicio)
        if materialized_count == 0:
            raise ValidationError("Não foi possível desmarcar este exercício sem remover a sessão.")

    sessao_exercicio.delete()
    return UnmarkExerciseDayResult(
        sessao_id=sessao_id,
        exercise_id=exercise_id,
        deleted_session=False,
        target_date=target_date,
    )


def _get_explicit_session_exercise_for_date(
    paciente: Paciente,
    exercicio: ExercicioCatalogo,
    target_date: date,
) -> SessaoExercicio | None:
    start_datetime, end_datetime = _day_datetime_range(target_date)
    return (
        SessaoExercicio.objects.select_related("sessao", "sessao__procedimento", "exercicio")
        .filter(
            sessao__procedimento__paciente=paciente,
            sessao__data_hora__gte=start_datetime,
            sessao__data_hora__lte=end_datetime,
            sessao__status__in=GRID_SESSION_STATUSES,
            exercicio=exercicio,
        )
        .order_by("sessao__data_hora", "pk")
        .first()
    )


def _get_fallback_session_for_date(
    paciente: Paciente,
    exercicio: ExercicioCatalogo,
    target_date: date,
) -> Sessao | None:
    start_datetime, end_datetime = _day_datetime_range(target_date)
    return (
        Sessao.objects.filter(
            procedimento__paciente=paciente,
            data_hora__gte=start_datetime,
            data_hora__lte=end_datetime,
            status__in=GRID_SESSION_STATUSES,
            procedimento__procedimento_exercicios__is_active=True,
            procedimento__procedimento_exercicios__exercicio=exercicio,
        )
        .annotate(
            active_session_exercise_count=Count(
                "sessao_exercicios",
                filter=Q(sessao_exercicios__is_active=True),
            )
        )
        .filter(active_session_exercise_count=0)
        .order_by("data_hora", "pk")
        .first()
    )


def _materialize_session_exercises_except(sessao: Sessao, excluded_exercise: ExercicioCatalogo) -> int:
    session_status = (
        sessao.status
        if sessao.status in GRID_SESSION_STATUSES
        else _session_status_for_marked_date(timezone.localtime(sessao.data_hora).date())
    )
    procedure_items = list(
        ProcedimentoExercicio.objects.filter(
            procedimento=sessao.procedimento,
        )
        .exclude(exercicio=excluded_exercise)
        .order_by("ordem", "created_at", "pk")
    )

    materialized_count = 0
    for procedure_item in procedure_items:
        _get_or_create_session_exercise(sessao, procedure_item, session_status)
        materialized_count += 1
    return materialized_count


def _is_tracking_created_session(sessao: Sessao) -> bool:
    return sessao.observacoes == TRACKING_SESSION_OBSERVATION


def _sync_session_status_for_mark(sessao: Sessao, desired_status: str) -> None:
    if desired_status == Sessao.STATUS_REALIZADA and sessao.status != Sessao.STATUS_REALIZADA:
        sessao.status = Sessao.STATUS_REALIZADA
    elif desired_status == Sessao.STATUS_AGENDADA and sessao.status not in GRID_SESSION_STATUSES:
        sessao.status = Sessao.STATUS_AGENDADA
    else:
        return

    sessao.save(update_fields=["status", "updated_at"])


def _get_or_create_session_exercise(
    sessao: Sessao,
    procedimento_exercicio: ProcedimentoExercicio,
    session_status: str,
) -> tuple[SessaoExercicio, bool]:
    existing = (
        SessaoExercicio.all_objects.filter(
            sessao=sessao,
            exercicio=procedimento_exercicio.exercicio,
        )
        .order_by("-is_active", "created_at", "pk")
        .first()
    )
    exercise_status = _exercise_status_for_session_status(session_status)

    if existing:
        update_fields = []
        if not existing.is_active:
            existing.is_active = True
            existing.deleted_at = None
            update_fields.extend(["is_active", "deleted_at"])
        if existing.status != exercise_status:
            existing.status = exercise_status
            update_fields.append("status")
        if update_fields:
            update_fields.append("updated_at")
            existing.save(update_fields=update_fields)
        return existing, False

    next_order = (
        SessaoExercicio.all_objects.filter(sessao=sessao, is_active=True).aggregate(max_order=Max("ordem"))[
            "max_order"
        ]
        or 0
    ) + 1
    return (
        SessaoExercicio.objects.create(
            sessao=sessao,
            exercicio=procedimento_exercicio.exercicio,
            ordem=next_order,
            series=procedimento_exercicio.series,
            repeticoes=procedimento_exercicio.repeticoes,
            frequencia=procedimento_exercicio.frequencia,
            progressao=procedimento_exercicio.progressao,
            observacoes=procedimento_exercicio.observacoes,
            status=exercise_status,
        ),
        True,
    )


def _session_status_for_marked_date(target_date: date) -> str:
    if target_date <= timezone.localdate():
        return Sessao.STATUS_REALIZADA
    return Sessao.STATUS_AGENDADA


def _exercise_status_for_session_status(session_status: str) -> str:
    if session_status == Sessao.STATUS_REALIZADA:
        return SessaoExercicio.STATUS_CONCLUIDO
    return SessaoExercicio.STATUS_PLANEJADO


def _default_session_datetime_for_date(target_date: date) -> datetime:
    duration_minutes = 60
    for hour in range(8, 20):
        candidate = timezone.make_aware(
            datetime.combine(target_date, time(hour=hour)),
            timezone.get_current_timezone(),
        )
        if find_schedule_conflict(start=candidate, duration_minutes=duration_minutes) is None:
            return candidate

    raise ValidationError("Não há horário livre para criar uma sessão neste dia.")


def _get_last_performed_dates_by_exercise(paciente: Paciente) -> dict[int, date]:
    dates_by_exercise = _get_session_exercise_dates_by_statuses(paciente, statuses=COMPLETED_SESSION_STATUSES)
    return {
        exercise_id: max(performed_dates)
        for exercise_id, performed_dates in dates_by_exercise.items()
        if performed_dates
    }


def _session_exercises_queryset_for_statuses(paciente: Paciente, statuses: set[str]):
    return SessaoExercicio.all_objects.filter(
        is_active=True,
        sessao__is_active=True,
        sessao__procedimento__is_active=True,
        sessao__procedimento__paciente=paciente,
        sessao__procedimento__paciente__is_active=True,
        sessao__procedimento__tipo_procedimento__is_active=True,
        sessao__status__in=statuses,
    )


def _sessions_without_explicit_exercises_queryset(paciente: Paciente, statuses: set[str]):
    return (
        Sessao.objects.filter(
            procedimento__paciente=paciente,
            status__in=statuses,
        )
        .annotate(
            active_session_exercise_count=Count(
                "sessao_exercicios",
                filter=Q(sessao_exercicios__is_active=True),
            )
        )
        .filter(active_session_exercise_count=0)
    )


def _get_exercise_universe(paciente: Paciente) -> dict[int, dict]:
    exercises: dict[int, dict] = {}

    procedure_rows = (
        ProcedimentoExercicio.all_objects.filter(
            is_active=True,
            procedimento__is_active=True,
            procedimento__paciente=paciente,
            procedimento__paciente__is_active=True,
            procedimento__tipo_procedimento__is_active=True,
        )
        .values(
            "exercicio_id",
            "exercicio__nome",
            "exercicio__categoria_id",
            "exercicio__categoria__nome",
            "ordem",
        )
        .order_by("procedimento__created_at", "procedimento_id", "ordem", "created_at", "pk")
    )
    session_rows = (
        SessaoExercicio.all_objects.filter(
            is_active=True,
            sessao__is_active=True,
            sessao__procedimento__is_active=True,
            sessao__procedimento__paciente=paciente,
            sessao__procedimento__paciente__is_active=True,
            sessao__procedimento__tipo_procedimento__is_active=True,
        )
        .values(
            "exercicio_id",
            "exercicio__nome",
            "exercicio__categoria_id",
            "exercicio__categoria__nome",
            "ordem",
        )
        .order_by("sessao__data_hora", "sessao_id", "ordem", "created_at", "pk")
    )

    for display_order, row in enumerate(procedure_rows, start=1):
        _add_exercise_data(exercises, row, display_order)

    session_display_start = len(exercises) + 1
    for display_offset, row in enumerate(session_rows):
        _add_exercise_data(exercises, row, session_display_start + display_offset)

    return exercises


def _add_exercise_data(exercises: dict[int, dict], row: dict, display_order: int) -> None:
    exercise_id = row["exercicio_id"]
    if exercise_id in exercises:
        return

    exercises[exercise_id] = {
        "exercise_id": exercise_id,
        "name": row["exercicio__nome"],
        "category_id": row["exercicio__categoria_id"],
        "category_name": row["exercicio__categoria__nome"] or "Sem categoria",
        "display_order": display_order,
        "exercise_order": row["ordem"] or display_order,
    }


def _exercise_display_order(item: dict) -> tuple[int, int, str, str, int]:
    return (
        item["display_order"],
        item["exercise_order"],
        item["category_name"].lower(),
        item["name"].lower(),
        item["exercise_id"],
    )


def _get_color_state(
    *,
    performed_in_last_session: bool,
    last_performed: date | None,
    today: date,
) -> str:
    if performed_in_last_session:
        return COLOR_RED
    if last_performed and (today - last_performed).days > 30:
        return COLOR_BLUE
    return COLOR_BLACK


def _get_day_temporal_state(value: date, today: date) -> str:
    if value < today:
        return DAY_PAST
    if value == today:
        return DAY_TODAY
    return DAY_FUTURE


def _aware_month_boundary(value: date) -> datetime:
    return timezone.make_aware(
        datetime.combine(value, time.min),
        timezone.get_current_timezone(),
    )


def _day_datetime_range(value: date) -> tuple[datetime, datetime]:
    current_timezone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(value, time.min), current_timezone),
        timezone.make_aware(datetime.combine(value, time.max), current_timezone),
    )


def _previous_month(value: date) -> date:
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _month_param(value: date) -> str:
    return value.strftime("%Y-%m")


__all__ = [
    "COLOR_BLACK",
    "COLOR_BLUE",
    "COLOR_RED",
    "DAY_FUTURE",
    "DAY_PAST",
    "DAY_TODAY",
    "MonthlyTrackingDay",
    "MonthlyExerciseDay",
    "MonthlyExerciseGroup",
    "MonthlyExerciseRow",
    "MonthlyExerciseTrackingTable",
    "MarkExerciseDayResult",
    "UnmarkExerciseDayResult",
    "build_monthly_exercise_tracking_table",
    "mark_exercise_day_for_patient",
    "parse_month_reference",
    "unmark_exercise_day_for_patient",
]
