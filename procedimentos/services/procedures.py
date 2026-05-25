from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from ..models import Procedimento, Sessao
from .scheduling import create_initial_session_for_procedure


@dataclass(frozen=True)
class ProcedureCreationResult:
    procedimento: Procedimento
    initial_session_created: bool


@transaction.atomic
def save_procedure_with_optional_initial_session(
    procedimento: Procedimento,
    *,
    create_initial_session: bool,
    initial_session_datetime: datetime | None = None,
    initial_session_duration_minutes: int | None = None,
) -> ProcedureCreationResult:
    procedimento.save()
    if create_initial_session:
        if initial_session_datetime is None or initial_session_duration_minutes is None:
            raise ValidationError("Informe data e duração para criar a primeira sessão.")
        create_initial_session_for_procedure(
            procedimento,
            data_hora=initial_session_datetime,
            duracao_minutos=initial_session_duration_minutes,
        )
        return ProcedureCreationResult(procedimento=procedimento, initial_session_created=True)

    return ProcedureCreationResult(procedimento=procedimento, initial_session_created=False)


def toggle_procedure_completion(procedimento: Procedimento) -> Procedimento:
    procedimento.concluido = not procedimento.concluido
    procedimento.save(update_fields=["concluido", "updated_at"])
    return procedimento


def update_session_status(sessao: Sessao, status: str) -> Sessao:
    allowed = {choice[0] for choice in Sessao.STATUS_CHOICES}
    if status not in allowed:
        raise ValidationError("Status de sessão inválido.")

    sessao.status = status
    sessao.save(update_fields=["status", "updated_at"])
    return sessao
