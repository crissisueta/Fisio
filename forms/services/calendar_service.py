from ..models import AnamneseGeral, AnamneseAcupuntura, FichaDrenagem, FichaExercicios
from django.utils.timezone import localtime


def build_calendar_events():
    """
    Collect date/time fields from relevant models and convert them into a unified event format
    for calendar integration.

    Returns:
        list: List of event dictionaries with keys: title, start, end, url, color
    """
    events = []

    # Anamnese Geral - Data de Avaliação
    for item in AnamneseGeral.objects.filter(data__isnull=False).select_related('paciente'):
        patient_name = item.paciente.nome if item.paciente else item.nome
        events.append({
            "title": f"Anamnese Geral - {patient_name}",
            # convert to local timezone before serializing; this adds the -03:00 offset
            "start": localtime(item.data).isoformat(),
            "end": None,  # Point-in-time event
            "url": f"/forms/anamnese-geral/{item.pk}/",
            "color": "#007bff",  # Blue
            "allDay": False
        })

    # Anamnese Acupuntura - Data da Consulta
    for item in AnamneseAcupuntura.objects.filter(data_consulta__isnull=False).select_related('paciente'):
        patient_name = item.paciente.nome if item.paciente else item.nome
        events.append({
            "title": f"Acupuntura - {patient_name}",
            "start": localtime(item.data_consulta).isoformat(),
            "end": None,
            "url": f"/forms/anamnese-acupuntura/{item.pk}/",
            "color": "#6f42c1",  # Purple
            "allDay": False
        })

    # Ficha Drenagem - Data da Avaliação
    for item in FichaDrenagem.objects.filter(data__isnull=False).select_related('paciente'):
        patient_name = item.paciente.nome if item.paciente else item.nome
        events.append({
            "title": f"Drenagem - {patient_name}",
            "start": localtime(item.data).isoformat(),
            "end": None,
            "url": f"/forms/drenagem/{item.pk}/",
            "color": "#28a745",  # Green
            "allDay": False
        })

    # Ficha Exercícios - Dia dos Exercícios
    for item in FichaExercicios.objects.filter(dia__isnull=False).select_related('paciente'):
        patient_name = item.paciente.nome if item.paciente else item.aluno
        events.append({
            "title": f"Exercícios - {patient_name}",
            "start": localtime(item.dia).isoformat(),
            "end": None,
            "url": f"/forms/exercicios/{item.pk}/",
            "color": "#fd7e14",  # Orange
            "allDay": False
        })

    return events