from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import ActivityLog
from core.services.activity import log_activity
from core.utils.datetime import ensure_aware_datetime, duration_minutes_for_times
from ..models import Procedimento, Sessao


WEEKDAY_CHOICES = [
    (0, "Segunda-feira"),
    (1, "Terça-feira"),
    (2, "Quarta-feira"),
    (3, "Quinta-feira"),
    (4, "Sexta-feira"),
    (5, "Sábado"),
    (6, "Domingo"),
]
WEEKDAY_LABELS = dict(WEEKDAY_CHOICES)


@dataclass
class BulkSessionGenerationResult:
    created_sessions: list[Sessao]
    skipped_conflicts: list[datetime]


@dataclass
class ScheduleConflict:
    conflicting_session: Sessao
    start: datetime
    end: datetime


def get_session_end_datetime(start: datetime, duration_minutes: int) -> datetime:
    return ensure_aware_datetime(start) + timedelta(minutes=duration_minutes)


def resequence_sessoes(procedimento: Procedimento | int) -> None:
    procedimento_id = procedimento.pk if isinstance(procedimento, Procedimento) else procedimento
    sessoes = list(Sessao.objects.filter(procedimento_id=procedimento_id).order_by("data_hora", "created_at", "pk"))

    for index, sessao in enumerate(sessoes, start=1):
        if sessao.numero != index:
            Sessao.objects.filter(pk=sessao.pk).update(numero=index, updated_at=timezone.now())


def find_schedule_conflict(
    *,
    start: datetime,
    duration_minutes: int,
    ignore_session_id: int | None = None,
) -> ScheduleConflict | None:
    start = ensure_aware_datetime(start)
    end = get_session_end_datetime(start, duration_minutes)

    queryset = (
        Sessao.objects.select_related("procedimento", "procedimento__paciente", "procedimento__tipo_procedimento")
        .filter(data_hora__lt=end)
        .exclude(status=Sessao.STATUS_CANCELADA)
    )

    if ignore_session_id:
        queryset = queryset.exclude(pk=ignore_session_id)

    for sessao in queryset.order_by("data_hora", "pk"):
        sessao_inicio = ensure_aware_datetime(sessao.data_hora)
        sessao_fim = get_session_end_datetime(sessao_inicio, sessao.duracao_minutos)
        if sessao_fim > start:
            return ScheduleConflict(conflicting_session=sessao, start=sessao_inicio, end=sessao_fim)

    return None


def validate_session_conflict(
    *,
    start: datetime,
    duration_minutes: int,
    ignore_session_id: int | None = None,
) -> None:
    conflict = find_schedule_conflict(
        start=start,
        duration_minutes=duration_minutes,
        ignore_session_id=ignore_session_id,
    )

    if not conflict:
        return

    conflito_inicio = timezone.localtime(conflict.start).strftime("%d/%m/%Y %H:%M")
    conflito_fim = timezone.localtime(conflict.end).strftime("%H:%M")
    raise ValidationError(f"Conflito de horário: este período já está ocupado ({conflito_inicio} - {conflito_fim}).")


@transaction.atomic
def create_session_for_procedimento(
    procedimento: Procedimento,
    *,
    data_hora: datetime,
    duracao_minutos: int = 60,
    status: str = Sessao.STATUS_AGENDADA,
    assinatura_confirmada: bool = False,
    observacoes: str = "",
    activity_user=None,
) -> Sessao:
    aware_datetime = ensure_aware_datetime(data_hora)
    validate_session_conflict(start=aware_datetime, duration_minutes=duracao_minutos)

    sessao = Sessao.objects.create(
        procedimento=procedimento,
        data_hora=aware_datetime,
        duracao_minutos=duracao_minutos,
        status=status,
        assinatura_confirmada=assinatura_confirmada,
        observacoes=observacoes,
    )
    resequence_sessoes(procedimento)
    sessao.refresh_from_db(fields=["numero"])
    _log_session_created(sessao, activity_user)
    return sessao


@transaction.atomic
def update_sessao(
    sessao: Sessao,
    *,
    data_hora: datetime,
    duracao_minutos: int,
    status: str,
    assinatura_confirmada: bool,
    observacoes: str,
    activity_user=None,
) -> Sessao:
    aware_datetime = ensure_aware_datetime(data_hora)
    old_data_hora = sessao.data_hora
    old_duration_minutes = sessao.duracao_minutos
    old_status = sessao.status
    validate_session_conflict(
        start=aware_datetime,
        duration_minutes=duracao_minutos,
        ignore_session_id=sessao.pk,
    )

    sessao.data_hora = aware_datetime
    sessao.duracao_minutos = duracao_minutos
    sessao.status = status
    sessao.assinatura_confirmada = assinatura_confirmada
    sessao.observacoes = observacoes
    sessao.save(
        update_fields=["data_hora", "duracao_minutos", "status", "assinatura_confirmada", "observacoes", "updated_at"]
    )
    resequence_sessoes(sessao.procedimento_id)
    sessao.refresh_from_db(fields=["numero"])
    _log_session_update(
        sessao,
        activity_user,
        old_data_hora=old_data_hora,
        old_duration_minutes=old_duration_minutes,
        old_status=old_status,
    )
    return sessao


def create_initial_session_for_procedure(
    procedimento: Procedimento,
    *,
    data_hora: datetime,
    duracao_minutos: int,
    activity_user=None,
) -> Sessao:
    return create_session_for_procedimento(
        procedimento,
        data_hora=data_hora,
        duracao_minutos=duracao_minutos,
        activity_user=activity_user,
    )


@transaction.atomic
def generate_sessions_for_month_by_weekday(
    procedimento: Procedimento,
    *,
    year: int,
    month: int,
    weekdays: list[int],
    start_time: time,
    end_time: time,
) -> BulkSessionGenerationResult:
    if not weekdays:
        raise ValidationError("Selecione ao menos um dia da semana para o agendamento em lote.")
    if end_time <= start_time:
        raise ValidationError("O horário final deve ser maior que o horário inicial.")

    duration_minutes = duration_minutes_for_times(start_time, end_time)
    _, month_days = calendar.monthrange(year, month)
    candidate_datetimes: list[datetime] = []

    for day in range(1, month_days + 1):
        current_date = date(year, month, day)
        if current_date.weekday() in weekdays:
            candidate_datetimes.append(ensure_aware_datetime(datetime.combine(current_date, start_time)))

    candidate_datetimes.sort()
    created_sessions: list[Sessao] = []
    skipped_conflicts: list[datetime] = []

    for candidate in candidate_datetimes:
        try:
            created_sessions.append(
                create_session_for_procedimento(
                    procedimento,
                    data_hora=candidate,
                    duracao_minutos=duration_minutes,
                )
            )
        except ValidationError:
            skipped_conflicts.append(candidate)

    return BulkSessionGenerationResult(
        created_sessions=created_sessions,
        skipped_conflicts=skipped_conflicts,
    )


def _log_session_created(sessao: Sessao, user) -> None:
    if not user:
        return
    log_activity(
        user=user,
        event_type="session.created",
        message=f"criou sessão para {_session_patient_name(sessao)}",
        level=ActivityLog.LEVEL_SUCCESS,
        metadata=_session_activity_metadata(sessao),
    )


def _log_session_update(
    sessao: Sessao,
    user,
    *,
    old_data_hora: datetime,
    old_duration_minutes: int,
    old_status: str,
) -> None:
    if not user:
        return

    if old_status != sessao.status and sessao.status == Sessao.STATUS_CANCELADA:
        log_activity(
            user=user,
            event_type="session.cancelled",
            message=f"cancelou sessão de {_session_patient_name(sessao)}",
            level=ActivityLog.LEVEL_WARNING,
            metadata=_session_activity_metadata(sessao, old_status=old_status),
        )
        return

    if old_data_hora != sessao.data_hora or old_duration_minutes != sessao.duracao_minutos:
        log_activity(
            user=user,
            event_type="session.rescheduled",
            message=f"reagendou sessão de {_session_patient_name(sessao)}",
            level=ActivityLog.LEVEL_INFO,
            metadata=_session_activity_metadata(sessao),
        )
        return

    if old_status != sessao.status:
        log_activity(
            user=user,
            event_type="session.status_updated",
            message=f"alterou status da sessão de {_session_patient_name(sessao)}",
            level=ActivityLog.LEVEL_INFO,
            metadata=_session_activity_metadata(sessao, old_status=old_status),
        )


def _session_patient_name(sessao: Sessao) -> str:
    return sessao.procedimento.paciente.nome


def _session_activity_metadata(sessao: Sessao, **extra) -> dict:
    metadata = {
        "session_id": sessao.pk,
        "procedure_id": sessao.procedimento_id,
        "patient_id": sessao.procedimento.paciente_id,
        "status": sessao.status,
        "scheduled_at": sessao.data_hora.isoformat(),
    }
    metadata.update(extra)
    return metadata
