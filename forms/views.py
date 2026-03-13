from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, TemplateView, UpdateView

from .forms import (
    AvaliacaoForm,
    CategoriaExercicioForm,
    ExercicioCatalogoForm,
    PacienteForm,
    ProcedimentoBulkScheduleForm,
    ProcedimentoForm,
    SessaoForm,
    SessaoExercicioSelectionForm,
    TipoProcedimentoForm,
)
from .models import (
    Avaliacao,
    CategoriaExercicio,
    ExercicioCatalogo,
    Paciente,
    Procedimento,
    Sessao,
    SessaoExercicio,
    TipoProcedimento,
)
from .services.calendar_service import build_calendar_events
from .services.exercise_history_service import SessionExerciseHistoryService
from .services.scheduling_service import (
    create_initial_session_for_procedure,
    create_session_for_procedimento,
    generate_sessions_for_month_by_weekday,
    update_sessao,
)


def _data_hora_ciente_fuso(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


class InternalPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, "Você não possui permissão para acessar esta área.")
        return super().handle_no_permission()


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pacientes_count"] = Paciente.objects.count()
        context["avaliacoes_count"] = Avaliacao.objects.count()
        context["procedimentos_count"] = Procedimento.objects.count()
        context["sessoes_count"] = Sessao.objects.count()
        context["procedimentos_concluidos_count"] = Procedimento.objects.filter(concluido=True).count()
        context["procedimentos_pendentes_count"] = Procedimento.objects.filter(concluido=False).count()
        return context


@login_required
def get_paciente_data(request, paciente_id):
    paciente = get_object_or_404(Paciente, pk=paciente_id)
    return JsonResponse(
        {
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
    )


class PacienteListView(LoginRequiredMixin, ListView):
    model = Paciente
    template_name = "forms/inscricao_list.html"
    context_object_name = "fichas"
    paginate_by = 10


class PacienteDetailView(LoginRequiredMixin, DetailView):
    model = Paciente
    template_name = "forms/inscricao_detail.html"
    context_object_name = "ficha"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["procedimentos"] = (
            self.object.procedimentos.select_related("tipo_procedimento")
            .prefetch_related("sessoes")
            .order_by("-created_at")
        )
        context["avaliacoes"] = self.object.avaliacoes.select_related("tipo_avaliacao").order_by("-data_hora")
        return context


class PacienteCreateView(LoginRequiredMixin, CreateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "forms/inscricao_form.html"
    success_url = reverse_lazy("inscricao-list")

    def form_valid(self, form):
        messages.success(self.request, "Paciente cadastrado com sucesso.")
        return super().form_valid(form)


class PacienteUpdateView(LoginRequiredMixin, UpdateView):
    model = Paciente
    form_class = PacienteForm
    template_name = "forms/inscricao_form.html"
    success_url = reverse_lazy("inscricao-list")

    def form_valid(self, form):
        messages.success(self.request, "Cadastro do paciente atualizado com sucesso.")
        return super().form_valid(form)


class PacienteDeleteView(LoginRequiredMixin, DeleteView):
    model = Paciente
    template_name = "forms/inscricao_confirm_delete.html"
    success_url = reverse_lazy("inscricao-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Paciente removido com sucesso.")
        return super().delete(request, *args, **kwargs)


class AvaliacaoListView(LoginRequiredMixin, ListView):
    model = Avaliacao
    template_name = "forms/avaliacao_list.html"
    context_object_name = "avaliacoes"
    paginate_by = 15

    def get_queryset(self):
        return Avaliacao.objects.select_related("paciente", "tipo_avaliacao").order_by("-data_hora")


class AvaliacaoDetailView(LoginRequiredMixin, DetailView):
    model = Avaliacao
    template_name = "forms/avaliacao_detail.html"
    context_object_name = "avaliacao"


class AvaliacaoCreateView(LoginRequiredMixin, CreateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = "forms/avaliacao_form.html"
    success_url = reverse_lazy("avaliacao-list")

    def form_valid(self, form):
        messages.success(self.request, "Avaliação registrada com sucesso.")
        return super().form_valid(form)


class AvaliacaoUpdateView(LoginRequiredMixin, UpdateView):
    model = Avaliacao
    form_class = AvaliacaoForm
    template_name = "forms/avaliacao_form.html"
    success_url = reverse_lazy("avaliacao-list")

    def form_valid(self, form):
        messages.success(self.request, "Avaliação atualizada com sucesso.")
        return super().form_valid(form)


class AvaliacaoDeleteView(LoginRequiredMixin, DeleteView):
    model = Avaliacao
    template_name = "forms/avaliacao_confirm_delete.html"
    success_url = reverse_lazy("avaliacao-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Avaliação removida com sucesso.")
        return super().delete(request, *args, **kwargs)


class ProcedimentoListView(LoginRequiredMixin, ListView):
    model = Procedimento
    template_name = "forms/procedure_list.html"
    context_object_name = "procedimentos"
    paginate_by = 15

    def get_queryset(self):
        queryset = Procedimento.objects.select_related("paciente", "tipo_procedimento").order_by("-created_at")
        paciente_id = self.request.GET.get("paciente")
        tipo_id = self.request.GET.get("tipo")
        if paciente_id:
            queryset = queryset.filter(paciente_id=paciente_id)
        if tipo_id:
            queryset = queryset.filter(tipo_procedimento_id=tipo_id)
        return queryset


class ProcedimentoDetailView(LoginRequiredMixin, DetailView):
    model = Procedimento
    template_name = "forms/procedure_detail.html"
    context_object_name = "procedimento"

    def get_queryset(self):
        return Procedimento.objects.select_related("paciente", "tipo_procedimento").prefetch_related(
            "sessoes",
            "procedimento_exercicios__exercicio__categoria",
            "sessoes__sessao_exercicios__exercicio__categoria",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        todas_sessoes = list(self.object.sessoes.order_by("data_hora"))
        agora = timezone.now()

        sessoes_futuras = [
            sess for sess in todas_sessoes
            if _data_hora_ciente_fuso(sess.data_hora) >= agora and sess.status == Sessao.STATUS_AGENDADA
        ]
        sessoes_passadas = [sess for sess in todas_sessoes if sess not in sessoes_futuras]

        context["proxima_sessao"] = sessoes_futuras[0] if sessoes_futuras else None
        context["sessoes_futuras"] = sessoes_futuras
        context["sessoes_passadas"] = sessoes_passadas
        context["sessao_form"] = SessaoForm()
        context["aba_ativa"] = "sessoes"
        context["exercicios_habilitados"] = self.object.tipo_procedimento.habilita_exercicios

        if self.object.tipo_procedimento.habilita_exercicios:
            exercicios_catalogo = list(
                ExercicioCatalogo.objects.filter(is_active=True, ativo=True)
                .select_related("categoria")
                .order_by("categoria__nome", "nome")
            )
            history_service = SessionExerciseHistoryService(self.object)
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


class ProcedimentoCreateView(LoginRequiredMixin, CreateView):
    model = Procedimento
    form_class = ProcedimentoForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["enable_schedule_fields"] = True
        return kwargs

    def form_valid(self, form):
        try:
            with transaction.atomic():
                self.object = form.save()
                modo_agendamento = form.cleaned_data["modo_agendamento"]

                if modo_agendamento == ProcedimentoForm.MODO_AGENDAMENTO_UNICO:
                    create_initial_session_for_procedure(
                        self.object,
                        data_hora=form.get_initial_session_datetime(),
                        duracao_minutos=form.get_initial_session_duration_minutes(),
                    )
        except ValidationError as exc:
            form.add_error("hora_sessao_inicial", exc.message)
            return self.form_invalid(form)

        if form.cleaned_data["modo_agendamento"] == ProcedimentoForm.MODO_AGENDAMENTO_UNICO:
            messages.success(self.request, "Procedimento criado com sucesso com a primeira sessão agendada.")
            return redirect("procedure-detail", pk=self.object.pk)

        messages.success(self.request, "Procedimento criado com sucesso. Agora preencha o período das sessões.")
        return redirect("procedure-bulk-schedule", pk=self.object.pk)


class ProcedimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Procedimento
    form_class = ProcedimentoForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["enable_schedule_fields"] = False
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Procedimento atualizado com sucesso.")
        return super().form_valid(form)


class ProcedimentoDeleteView(LoginRequiredMixin, DeleteView):
    model = Procedimento
    template_name = "forms/procedure_confirm_delete.html"
    success_url = reverse_lazy("procedure-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Procedimento removido com sucesso.")
        return super().delete(request, *args, **kwargs)


class ProcedimentoBulkScheduleView(LoginRequiredMixin, FormView):
    template_name = "forms/procedure_bulk_schedule.html"
    form_class = ProcedimentoBulkScheduleForm

    def dispatch(self, request, *args, **kwargs):
        self.procedimento = get_object_or_404(
            Procedimento.objects.select_related("paciente", "tipo_procedimento"),
            pk=kwargs["pk"],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        now = timezone.localdate()
        initial["referencia_mes"] = now.replace(day=1)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["procedimento"] = self.procedimento
        return context

    def form_valid(self, form):
        referencia_mes = form.cleaned_data["referencia_mes"]
        result = generate_sessions_for_month_by_weekday(
            self.procedimento,
            year=referencia_mes.year,
            month=referencia_mes.month,
            weekdays=form.cleaned_data["dias_semana"],
            start_time=form.cleaned_data["hora_inicial"],
            end_time=form.cleaned_data["hora_final"],
        )

        if not result.created_sessions:
            messages.warning(
                self.request,
                "Nenhuma sessão foi criada. Todos os horários selecionados já possuíam conflito.",
            )
        else:
            messages.success(
                self.request,
                f"{len(result.created_sessions)} sessão(ões) criada(s) com sucesso para este procedimento.",
            )

        if result.skipped_conflicts:
            skipped_labels = ", ".join(
                timezone.localtime(conflict).strftime("%d/%m/%Y %H:%M")
                for conflict in result.skipped_conflicts
            )
            messages.warning(
                self.request,
                f"{len(result.skipped_conflicts)} sessão(ões) foram ignoradas por conflito de horário: {skipped_labels}.",
            )

        return redirect("procedure-detail", pk=self.procedimento.pk)


@login_required
@require_POST
def toggle_procedimento_concluido(request, pk):
    procedimento = get_object_or_404(Procedimento, pk=pk)
    procedimento.concluido = not procedimento.concluido
    procedimento.save(update_fields=["concluido", "updated_at"])
    estado = "concluído" if procedimento.concluido else "pendente"
    messages.success(request, f"Procedimento marcado como {estado}.")
    return redirect("procedure-detail", pk=procedimento.pk)


@login_required
@require_POST
def add_sessao(request, pk):
    procedimento = get_object_or_404(Procedimento, pk=pk)
    form = SessaoForm(request.POST)
    if form.is_valid():
        try:
            create_session_for_procedimento(
                procedimento,
                data_hora=form.cleaned_data["data_hora"],
                duracao_minutos=form.get_duration_minutes(),
                status=form.cleaned_data["status"],
                assinatura_confirmada=form.cleaned_data["assinatura_confirmada"],
                observacoes=form.cleaned_data["observacoes"],
            )
            messages.success(request, "Sessão adicionada com sucesso.")
        except ValidationError as exc:
            messages.warning(request, exc.message)
    else:
        messages.error(request, "Não foi possível adicionar a sessão. Verifique os dados informados.")
    return redirect("procedure-detail", pk=procedimento.pk)


@login_required
@require_POST
def edit_sessao(request, session_id):
    sessao = get_object_or_404(Sessao, pk=session_id)
    form = SessaoForm(request.POST, instance=sessao)
    if form.is_valid():
        try:
            update_sessao(
                sessao,
                data_hora=form.cleaned_data["data_hora"],
                duracao_minutos=form.get_duration_minutes(),
                status=form.cleaned_data["status"],
                assinatura_confirmada=form.cleaned_data["assinatura_confirmada"],
                observacoes=form.cleaned_data["observacoes"],
            )
            messages.success(request, "Sessão atualizada com sucesso.")
        except ValidationError as exc:
            messages.warning(request, exc.message)
    else:
        messages.error(request, "Não foi possível atualizar a sessão.")
    return redirect("procedure-detail", pk=sessao.procedimento_id)


@login_required
@require_POST
def update_status_sessao(request, session_id, status):
    sessao = get_object_or_404(Sessao, pk=session_id)
    allowed = {choice[0] for choice in Sessao.STATUS_CHOICES}
    if status not in allowed:
        messages.error(request, "Status de sessão inválido.")
        return redirect("procedure-detail", pk=sessao.procedimento_id)

    sessao.status = status
    sessao.save(update_fields=["status", "updated_at"])
    messages.success(request, "Status da sessão atualizado com sucesso.")
    return redirect("procedure-detail", pk=sessao.procedimento_id)


@login_required
@require_POST
def update_sessao_exercicios(request, session_id):
    sessao = get_object_or_404(
        Sessao.objects.select_related("procedimento", "procedimento__tipo_procedimento", "procedimento__paciente"),
        pk=session_id,
    )
    procedimento = sessao.procedimento
    if not procedimento.tipo_procedimento.habilita_exercicios:
        messages.error(request, "Este tipo de procedimento não possui gerenciamento de exercícios habilitado.")
        return redirect("procedure-detail", pk=procedimento.pk)

    legacy_items = list(procedimento.procedimento_exercicios.filter(is_active=True).select_related("exercicio"))
    fallback_ids = [item.exercicio_id for item in legacy_items]
    form = SessaoExercicioSelectionForm(request.POST, sessao=sessao, selected_ids=fallback_ids)
    if not form.is_valid():
        messages.error(request, "Não foi possível atualizar os exercícios da sessão.")
        return redirect("procedure-detail", pk=procedimento.pk)

    exercicios_selecionados = list(form.cleaned_data["exercicios"])
    selecionados_ids = {exercicio.pk for exercicio in exercicios_selecionados}

    existentes = {
        item.exercicio_id: item
        for item in SessaoExercicio.all_objects.filter(sessao=sessao).select_related("exercicio")
    }
    legacy_by_exercicio = {item.exercicio_id: item for item in legacy_items}

    for ordem, exercicio in enumerate(exercicios_selecionados, start=1):
        item = existentes.get(exercicio.pk)
        if item:
            update_fields = []
            if not item.is_active:
                item.is_active = True
                item.deleted_at = None
                update_fields.extend(["is_active", "deleted_at"])
            if item.ordem != ordem:
                item.ordem = ordem
                update_fields.append("ordem")
            if update_fields:
                if hasattr(item, "updated_at"):
                    update_fields.append("updated_at")
                item.save(update_fields=update_fields)
        else:
            legacy_item = legacy_by_exercicio.get(exercicio.pk)
            SessaoExercicio.objects.create(
                sessao=sessao,
                exercicio=exercicio,
                ordem=ordem,
                series=legacy_item.series if legacy_item else "",
                repeticoes=legacy_item.repeticoes if legacy_item else "",
                frequencia=legacy_item.frequencia if legacy_item else "",
                progressao=legacy_item.progressao if legacy_item else "",
                observacoes=legacy_item.observacoes if legacy_item else "",
                status=legacy_item.status if legacy_item else SessaoExercicio.STATUS_PLANEJADO,
            )

    ids_para_desativar = [
        item.pk
        for exercicio_id, item in existentes.items()
        if exercicio_id not in selecionados_ids and item.is_active
    ]
    if ids_para_desativar:
        SessaoExercicio.objects.filter(pk__in=ids_para_desativar).delete()

    messages.success(request, f"Exercícios da sessão {sessao.numero or '-'} atualizados com sucesso.")
    return redirect(f"{reverse_lazy('procedure-detail', kwargs={'pk': procedimento.pk})}#sessao-{sessao.pk}")


@login_required
def calendar_events(request):
    events = build_calendar_events()
    return JsonResponse(events, safe=False)


class CalendarDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/calendar.html"


class CategoriaExercicioListView(InternalPermissionMixin, ListView):
    model = CategoriaExercicio
    template_name = "forms/exercise_category_list.html"
    context_object_name = "categorias"
    paginate_by = 15
    permission_required = "forms.view_categoriaexercicio"

    def get_queryset(self):
        queryset = CategoriaExercicio.all_objects.order_by("nome")
        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "ativas")

        if search:
            queryset = queryset.filter(nome__icontains=search)
        if status == "ativas":
            queryset = queryset.filter(is_active=True)
        elif status == "inativas":
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["status_filter"] = self.request.GET.get("status", "ativas")
        return context


class CategoriaExercicioCreateView(InternalPermissionMixin, CreateView):
    model = CategoriaExercicio
    form_class = CategoriaExercicioForm
    template_name = "forms/exercise_category_form.html"
    success_url = reverse_lazy("exercise-category-list")
    permission_required = "forms.add_categoriaexercicio"

    def form_valid(self, form):
        messages.success(self.request, "Categoria de exercício cadastrada com sucesso.")
        return super().form_valid(form)


class CategoriaExercicioUpdateView(InternalPermissionMixin, UpdateView):
    model = CategoriaExercicio
    form_class = CategoriaExercicioForm
    template_name = "forms/exercise_category_form.html"
    success_url = reverse_lazy("exercise-category-list")
    permission_required = "forms.change_categoriaexercicio"
    queryset = CategoriaExercicio.all_objects.all()

    def form_valid(self, form):
        messages.success(self.request, "Categoria de exercício atualizada com sucesso.")
        return super().form_valid(form)


class CategoriaExercicioDeleteView(InternalPermissionMixin, DeleteView):
    model = CategoriaExercicio
    template_name = "forms/exercise_category_confirm_delete.html"
    success_url = reverse_lazy("exercise-category-list")
    permission_required = "forms.delete_categoriaexercicio"
    queryset = CategoriaExercicio.all_objects.all()

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Categoria de exercício desativada com sucesso.")
        return super().delete(request, *args, **kwargs)


class ExercicioCatalogoListView(InternalPermissionMixin, ListView):
    model = ExercicioCatalogo
    template_name = "forms/exercise_list.html"
    context_object_name = "exercicios"
    paginate_by = 15
    permission_required = "forms.view_exerciciocatalogo"

    def get_queryset(self):
        queryset = ExercicioCatalogo.all_objects.select_related("categoria").order_by("nome")
        search = self.request.GET.get("q", "").strip()
        categoria_id = self.request.GET.get("categoria", "").strip()
        status = self.request.GET.get("status", "ativos")

        if search:
            queryset = queryset.filter(nome__icontains=search)
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        if status == "ativos":
            queryset = queryset.filter(is_active=True)
        elif status == "inativos":
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["selected_category"] = self.request.GET.get("categoria", "").strip()
        context["status_filter"] = self.request.GET.get("status", "ativos")
        context["categorias_disponiveis"] = CategoriaExercicio.objects.order_by("nome")
        return context


class ExercicioCatalogoCreateView(InternalPermissionMixin, CreateView):
    model = ExercicioCatalogo
    form_class = ExercicioCatalogoForm
    template_name = "forms/exercise_form.html"
    success_url = reverse_lazy("exercise-list")
    permission_required = "forms.add_exerciciocatalogo"

    def form_valid(self, form):
        messages.success(self.request, "Exercício cadastrado com sucesso.")
        return super().form_valid(form)


class ExercicioCatalogoUpdateView(InternalPermissionMixin, UpdateView):
    model = ExercicioCatalogo
    form_class = ExercicioCatalogoForm
    template_name = "forms/exercise_form.html"
    success_url = reverse_lazy("exercise-list")
    permission_required = "forms.change_exerciciocatalogo"
    queryset = ExercicioCatalogo.all_objects.select_related("categoria")

    def form_valid(self, form):
        messages.success(self.request, "Exercício atualizado com sucesso.")
        return super().form_valid(form)


class ExercicioCatalogoDeleteView(InternalPermissionMixin, DeleteView):
    model = ExercicioCatalogo
    template_name = "forms/exercise_confirm_delete.html"
    success_url = reverse_lazy("exercise-list")
    permission_required = "forms.delete_exerciciocatalogo"
    queryset = ExercicioCatalogo.all_objects.select_related("categoria")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Exercício desativado com sucesso.")
        return super().delete(request, *args, **kwargs)


class TipoProcedimentoListView(InternalPermissionMixin, ListView):
    model = TipoProcedimento
    template_name = "forms/procedure_type_list.html"
    context_object_name = "tipos_procedimento"
    paginate_by = 15
    permission_required = "forms.view_tipoprocedimento"

    def get_queryset(self):
        queryset = TipoProcedimento.all_objects.order_by("nome")
        search = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "ativos")

        if search:
            queryset = queryset.filter(nome__icontains=search)
        if status == "ativos":
            queryset = queryset.filter(is_active=True)
        elif status == "inativos":
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["status_filter"] = self.request.GET.get("status", "ativos")
        return context


class TipoProcedimentoCreateView(InternalPermissionMixin, CreateView):
    model = TipoProcedimento
    form_class = TipoProcedimentoForm
    template_name = "forms/procedure_type_form.html"
    success_url = reverse_lazy("procedure-type-list")
    permission_required = "forms.add_tipoprocedimento"

    def form_valid(self, form):
        messages.success(self.request, "Tipo de procedimento cadastrado com sucesso.")
        return super().form_valid(form)


class TipoProcedimentoUpdateView(InternalPermissionMixin, UpdateView):
    model = TipoProcedimento
    form_class = TipoProcedimentoForm
    template_name = "forms/procedure_type_form.html"
    success_url = reverse_lazy("procedure-type-list")
    permission_required = "forms.change_tipoprocedimento"
    queryset = TipoProcedimento.all_objects.all()

    def form_valid(self, form):
        messages.success(self.request, "Tipo de procedimento atualizado com sucesso.")
        return super().form_valid(form)


class TipoProcedimentoDeleteView(InternalPermissionMixin, DeleteView):
    model = TipoProcedimento
    template_name = "forms/procedure_type_confirm_delete.html"
    success_url = reverse_lazy("procedure-type-list")
    permission_required = "forms.delete_tipoprocedimento"
    queryset = TipoProcedimento.all_objects.all()

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Tipo de procedimento desativado com sucesso.")
        return super().delete(request, *args, **kwargs)
