from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import ActivityLog
from core.services.activity import log_activity
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
    activity_user=None,
) -> ProcedureCreationResult:
    procedimento.save()
    _log_procedure_activity(
        procedimento,
        activity_user,
        event_type="procedure.created",
        message=f"criou procedimento de {procedimento.paciente.nome}",
        level=ActivityLog.LEVEL_SUCCESS,
    )
    if create_initial_session:
        if initial_session_datetime is None or initial_session_duration_minutes is None:
            raise ValidationError("Informe data e duração para criar a primeira sessão.")
        create_initial_session_for_procedure(
            procedimento,
            data_hora=initial_session_datetime,
            duracao_minutos=initial_session_duration_minutes,
            activity_user=activity_user,
        )
        return ProcedureCreationResult(procedimento=procedimento, initial_session_created=True)

    return ProcedureCreationResult(procedimento=procedimento, initial_session_created=False)


def toggle_procedure_completion(procedimento: Procedimento, *, activity_user=None) -> Procedimento:
    procedimento.concluido = not procedimento.concluido
    procedimento.save(update_fields=["concluido", "updated_at"])
    event_type = "procedure.completed" if procedimento.concluido else "procedure.reopened"
    action = "concluiu" if procedimento.concluido else "reabriu"
    _log_procedure_activity(
        procedimento,
        activity_user,
        event_type=event_type,
        message=f"{action} procedimento de {procedimento.paciente.nome}",
        level=ActivityLog.LEVEL_SUCCESS if procedimento.concluido else ActivityLog.LEVEL_INFO,
    )
    return procedimento


def update_session_status(sessao: Sessao, status: str, *, activity_user=None) -> Sessao:
    allowed = {choice[0] for choice in Sessao.STATUS_CHOICES}
    if status not in allowed:
        raise ValidationError("Status de sessão inválido.")

    old_status = sessao.status
    sessao.status = status
    sessao.save(update_fields=["status", "updated_at"])
    if activity_user and old_status != status:
        if status == Sessao.STATUS_CANCELADA:
            log_activity(
                user=activity_user,
                event_type="session.cancelled",
                message=f"cancelou sessão de {sessao.procedimento.paciente.nome}",
                level=ActivityLog.LEVEL_WARNING,
                metadata=_session_status_metadata(sessao, old_status=old_status),
            )
        else:
            log_activity(
                user=activity_user,
                event_type="session.status_updated",
                message=f"alterou status da sessão de {sessao.procedimento.paciente.nome}",
                level=ActivityLog.LEVEL_INFO,
                metadata=_session_status_metadata(sessao, old_status=old_status),
            )
    return sessao


def _log_procedure_activity(
    procedimento: Procedimento,
    user,
    *,
    event_type: str,
    message: str,
    level: str,
) -> None:
    if not user:
        return
    log_activity(
        user=user,
        event_type=event_type,
        message=message,
        level=level,
        metadata={
            "procedure_id": procedimento.pk,
            "patient_id": procedimento.paciente_id,
            "procedure_type_id": procedimento.tipo_procedimento_id,
        },
    )


def _session_status_metadata(sessao: Sessao, **extra) -> dict:
    metadata = {
        "session_id": sessao.pk,
        "procedure_id": sessao.procedimento_id,
        "patient_id": sessao.procedimento.paciente_id,
        "status": sessao.status,
    }
    metadata.update(extra)
    return metadata
