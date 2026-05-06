from django.utils import timezone

from ..core.utils.datetime import ensure_aware_datetime
from ..exercicios.models import ExercicioCatalogo
from ..exercicios.services.history import SessionExerciseHistoryService
from ..exercicios.forms import SessaoExercicioSelectionForm
from .forms import SessaoForm
from .models import Procedimento, Sessao, TipoProcedimento


def procedimento_list_queryset(request):
    queryset = Procedimento.objects.select_related("paciente", "tipo_procedimento").order_by("-created_at")
    paciente_id = request.GET.get("paciente")
    tipo_id = request.GET.get("tipo")
    if paciente_id:
        queryset = queryset.filter(paciente_id=paciente_id)
    if tipo_id:
        queryset = queryset.filter(tipo_procedimento_id=tipo_id)
    return queryset


def procedimento_detail_queryset():
    return Procedimento.objects.select_related("paciente", "tipo_procedimento").prefetch_related(
        "sessoes",
        "procedimento_exercicios__exercicio__categoria",
        "sessoes__sessao_exercicios__exercicio__categoria",
    )


def get_procedimento_for_bulk_schedule(pk):
    return Procedimento.objects.select_related("paciente", "tipo_procedimento").get(pk=pk)


def build_procedimento_detail_context(procedimento: Procedimento):
    todas_sessoes = list(procedimento.sessoes.order_by("data_hora"))
    agora = timezone.now()
    sessoes_futuras = [
        sess
        for sess in todas_sessoes
        if ensure_aware_datetime(sess.data_hora) >= agora and sess.status == Sessao.STATUS_AGENDADA
    ]
    sessoes_passadas = [sess for sess in todas_sessoes if sess not in sessoes_futuras]

    context = {
        "proxima_sessao": sessoes_futuras[0] if sessoes_futuras else None,
        "sessoes_futuras": sessoes_futuras,
        "sessoes_passadas": sessoes_passadas,
        "sessao_form": SessaoForm(),
        "aba_ativa": "sessoes",
        "exercicios_habilitados": procedimento.tipo_procedimento.habilita_exercicios,
    }

    if procedimento.tipo_procedimento.habilita_exercicios:
        exercicios_catalogo = list(
            ExercicioCatalogo.objects.filter(is_active=True, ativo=True)
            .select_related("categoria")
            .order_by("categoria__nome", "nome")
        )
        history_service = SessionExerciseHistoryService(procedimento)
        for sessao in todas_sessoes:
            selected_ids, _source = history_service.get_selected_ids_for_session(sessao)
            form = SessaoExercicioSelectionForm(sessao=sessao, selected_ids=selected_ids)
            selected_ids = set(form.fields["exercicios"].initial)
            status_map = history_service.get_status_map_for_session(sessao, exercicios_catalogo)
            sessao.exercicio_modal_grupos = form.get_exercicios_agrupados(status_map)
            sessao.exercicios_selecionados_ids = selected_ids
            sessao.exercicio_selection_source = history_service.get_selection_source_for_session(sessao)
            sessao.exercicio_itens = history_service.get_assigned_items_for_session(sessao)

    return context


def tipo_procedimento_list_queryset(request):
    queryset = TipoProcedimento.all_objects.order_by("nome")
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "ativos")

    if search:
        queryset = queryset.filter(nome__icontains=search)
    if status == "ativos":
        queryset = queryset.filter(is_active=True)
    elif status == "inativos":
        queryset = queryset.filter(is_active=False)

    return queryset
