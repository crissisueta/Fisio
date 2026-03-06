from django.utils import timezone
from django.utils.timezone import localtime
from unicodedata import normalize

from ..models import ProcedureSession


DEFAULT_PROCEDURE_COLOR = "#0d6efd"
PROCEDURE_TYPE_COLORS = {
    "anamnese geral": "#0d6efd",
    "acupuntura": "#6f42c1",
    "drenagem linfatica": "#20c997",
    "exercicios": "#fd7e14",
}


def _normalize_datetime(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _normalize_key(value):
    normalized = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.strip().lower()


def _get_procedure_color(procedure_type_name):
    return PROCEDURE_TYPE_COLORS.get(_normalize_key(procedure_type_name), DEFAULT_PROCEDURE_COLOR)


def build_calendar_events():
    """Build calendar events from ProcedureSession records only."""
    events = []

    queryset = ProcedureSession.objects.select_related(
        "procedure",
        "procedure__patient",
        "procedure__procedure_type",
    ).order_by("scheduled_datetime")

    for session in queryset:
        scheduled = _normalize_datetime(session.scheduled_datetime)
        patient_name = session.procedure.patient.nome
        procedure_name = session.procedure.procedure_type.name
        procedure_color = _get_procedure_color(procedure_name)

        events.append(
            {
                "title": f"{patient_name} - {procedure_name}",
                "start": localtime(scheduled).isoformat(),
                "end": None,
                "url": f"/forms/procedures/{session.procedure_id}/",
                "procedure_type": procedure_name,
                "procedure_color": procedure_color,
                "is_complete": session.status == ProcedureSession.STATUS_COMPLETED,
                "allDay": False,
            }
        )

    return events
