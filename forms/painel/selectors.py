from ..avaliacoes.models import Avaliacao
from ..pacientes.models import Paciente
from ..procedimentos.models import Procedimento, Sessao


def get_dashboard_counts():
    return {
        "pacientes_count": Paciente.objects.count(),
        "avaliacoes_count": Avaliacao.objects.count(),
        "procedimentos_count": Procedimento.objects.count(),
        "sessoes_count": Sessao.objects.count(),
        "procedimentos_concluidos_count": Procedimento.objects.filter(concluido=True).count(),
        "procedimentos_pendentes_count": Procedimento.objects.filter(concluido=False).count(),
    }

