from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from ...pacientes.models import Paciente
from ...procedimentos.models import Sessao
from ..models import ProcedimentoExercicio, SessaoExercicio


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
    for exercise_data in sorted(
        exercise_universe.values(),
        key=lambda item: (item["category_name"].lower(), item["name"].lower(), item["exercise_id"]),
    ):
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
        )
        .distinct()
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
        )
        .distinct()
    )

    for row in procedure_rows:
        _add_exercise_data(exercises, row)
    for row in session_rows:
        _add_exercise_data(exercises, row)

    return exercises


def _add_exercise_data(exercises: dict[int, dict], row: dict) -> None:
    exercise_id = row["exercicio_id"]
    if exercise_id in exercises:
        return

    exercises[exercise_id] = {
        "exercise_id": exercise_id,
        "name": row["exercicio__nome"],
        "category_id": row["exercicio__categoria_id"],
        "category_name": row["exercicio__categoria__nome"] or "Sem categoria",
    }


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
    "build_monthly_exercise_tracking_table",
    "parse_month_reference",
]
