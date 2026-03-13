from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, time

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

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


def ensure_aware_datetime(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def resequence_sessoes(procedimento: Procedimento | int) -> None:
    procedimento_id = procedimento.pk if isinstance(procedimento, Procedimento) else procedimento
    sessoes = list(
        Sessao.objects.filter(procedimento_id=procedimento_id)
        .order_by("data_hora", "created_at", "pk")
    )

    for index, sessao in enumerate(sessoes, start=1):
        if sessao.numero != index:
            Sessao.objects.filter(pk=sessao.pk).update(numero=index, updated_at=timezone.now())


def _validate_session_collision(
    procedimento: Procedimento,
    data_hora: datetime,
    *,
    ignore_session_id: int | None = None,
) -> None:
    aware_datetime = ensure_aware_datetime(data_hora)

    same_procedure = Sessao.objects.filter(procedimento=procedimento, data_hora=aware_datetime)
    same_patient = Sessao.objects.filter(
        procedimento__paciente=procedimento.paciente,
        data_hora=aware_datetime,
    )

    if ignore_session_id:
        same_procedure = same_procedure.exclude(pk=ignore_session_id)
        same_patient = same_patient.exclude(pk=ignore_session_id)

    if same_procedure.exists():
        raise ValidationError("Já existe uma sessão deste procedimento agendada para esta data e horário.")

    if same_patient.exists():
        raise ValidationError("O paciente já possui outra sessão agendada para esta data e horário.")


@transaction.atomic
def create_session_for_procedimento(
    procedimento: Procedimento,
    *,
    data_hora: datetime,
    status: str = Sessao.STATUS_AGENDADA,
    assinatura_confirmada: bool = False,
    observacoes: str = "",
) -> Sessao:
    aware_datetime = ensure_aware_datetime(data_hora)
    _validate_session_collision(procedimento, aware_datetime)

    sessao = Sessao.objects.create(
        procedimento=procedimento,
        data_hora=aware_datetime,
        status=status,
        assinatura_confirmada=assinatura_confirmada,
        observacoes=observacoes,
    )
    resequence_sessoes(procedimento)
    sessao.refresh_from_db(fields=["numero"])
    return sessao


@transaction.atomic
def update_sessao(
    sessao: Sessao,
    *,
    data_hora: datetime,
    status: str,
    assinatura_confirmada: bool,
    observacoes: str,
) -> Sessao:
    aware_datetime = ensure_aware_datetime(data_hora)
    _validate_session_collision(sessao.procedimento, aware_datetime, ignore_session_id=sessao.pk)

    sessao.data_hora = aware_datetime
    sessao.status = status
    sessao.assinatura_confirmada = assinatura_confirmada
    sessao.observacoes = observacoes
    sessao.save(update_fields=["data_hora", "status", "assinatura_confirmada", "observacoes", "updated_at"])
    resequence_sessoes(sessao.procedimento_id)
    sessao.refresh_from_db(fields=["numero"])
    return sessao


def create_initial_session_for_procedure(
    procedimento: Procedimento,
    *,
    data_hora: datetime,
) -> Sessao:
    return create_session_for_procedimento(procedimento, data_hora=data_hora)


@transaction.atomic
def generate_sessions_for_month_by_weekday(
    procedimento: Procedimento,
    *,
    year: int,
    month: int,
    weekdays: list[int],
    start_time: time,
) -> BulkSessionGenerationResult:
    if not weekdays:
        raise ValidationError("Selecione ao menos um dia da semana para o agendamento em lote.")

    _, month_days = calendar.monthrange(year, month)
    candidate_datetimes: list[datetime] = []

    for day in range(1, month_days + 1):
        current_date = date(year, month, day)
        if current_date.weekday() in weekdays:
            candidate_datetimes.append(
                ensure_aware_datetime(datetime.combine(current_date, start_time))
            )

    candidate_datetimes.sort()
    created_sessions: list[Sessao] = []
    skipped_conflicts: list[datetime] = []

    for candidate in candidate_datetimes:
        try:
            created_sessions.append(
                create_session_for_procedimento(
                    procedimento,
                    data_hora=candidate,
                )
            )
        except ValidationError:
            skipped_conflicts.append(candidate)

    return BulkSessionGenerationResult(
        created_sessions=created_sessions,
        skipped_conflicts=skipped_conflicts,
    )
