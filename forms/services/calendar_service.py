from unicodedata import normalize

from django.utils import timezone
from django.utils.timezone import localtime

from ..models import Sessao


COR_PADRAO_PROCEDIMENTO = "#0d6efd"
CORES_TIPO_PROCEDIMENTO = {
    "fisioterapia": "#0d6efd",
    "acupuntura": "#6f42c1",
    "drenagem linfatica": "#20c997",
    "pilates": "#fd7e14",
}


def _normalizar_data_hora(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _normalizar_chave(value):
    normalized = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return normalized.strip().lower()


def _cor_procedimento(nome_tipo):
    return CORES_TIPO_PROCEDIMENTO.get(_normalizar_chave(nome_tipo), COR_PADRAO_PROCEDIMENTO)


def build_calendar_events():
    """Monta eventos do calendário usando somente registros de Sessão."""
    events = []

    queryset = Sessao.objects.select_related(
        "procedimento",
        "procedimento__paciente",
        "procedimento__tipo_procedimento",
    ).order_by("data_hora")

    for sessao in queryset:
        data_hora = _normalizar_data_hora(sessao.data_hora)
        paciente_nome = sessao.procedimento.paciente.nome
        tipo_nome = sessao.procedimento.tipo_procedimento.nome

        events.append(
            {
                "title": f"{paciente_nome} - {tipo_nome}",
                "start": localtime(data_hora).isoformat(),
                "end": None,
                "url": f"/forms/procedimentos/{sessao.procedimento_id}/",
                "procedure_type": tipo_nome,
                "procedure_color": _cor_procedimento(tipo_nome),
                "is_complete": sessao.procedimento.concluido,
                "allDay": False,
            }
        )

    return events
