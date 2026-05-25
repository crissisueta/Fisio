from .models import Avaliacao


def avaliacao_list_queryset():
    return Avaliacao.objects.select_related("paciente", "tipo_avaliacao").order_by("-data_hora")

