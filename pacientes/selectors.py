from django.utils import timezone

from .models import Paciente


def get_paciente_detail_context(paciente: Paciente):
    return {
        "procedimentos": (
            paciente.procedimentos.select_related("tipo_procedimento").prefetch_related("sessoes").order_by("-created_at")
        ),
        "avaliacoes": paciente.avaliacoes.select_related("tipo_avaliacao").order_by("-data_hora"),
    }


def serialize_paciente_summary(paciente: Paciente):
    return {
        "nome": paciente.nome,
        "profissao": paciente.profissao,
        "data_nascimento": paciente.data_nascimento.isoformat(),
        "endereco": paciente.endereco,
        "telefone": paciente.telefone,
        "celular": paciente.celular,
        "idade": (timezone.now().date() - paciente.data_nascimento).days // 365,
        "procedimentos_count": paciente.procedimentos.count(),
        "avaliacoes_count": paciente.avaliacoes.count(),
    }

