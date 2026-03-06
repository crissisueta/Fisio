from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import AvaliacaoForm, PacienteForm, ProcedimentoForm, SessaoForm
from .models import Avaliacao, Paciente, Procedimento, Sessao
from .services.calendar_service import build_calendar_events


def _data_hora_ciente_fuso(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


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
        return Procedimento.objects.select_related("paciente", "tipo_procedimento").prefetch_related("sessoes")

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
        return context


class ProcedimentoCreateView(LoginRequiredMixin, CreateView):
    model = Procedimento
    form_class = ProcedimentoForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

    def form_valid(self, form):
        messages.success(self.request, "Procedimento criado com sucesso.")
        return super().form_valid(form)


class ProcedimentoUpdateView(LoginRequiredMixin, UpdateView):
    model = Procedimento
    form_class = ProcedimentoForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

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
        sessao = form.save(commit=False)
        sessao.procedimento = procedimento
        sessao.save()
        messages.success(request, "Sessão adicionada com sucesso.")
    else:
        messages.error(request, "Não foi possível adicionar a sessão. Verifique os dados informados.")
    return redirect("procedure-detail", pk=procedimento.pk)


@login_required
@require_POST
def edit_sessao(request, session_id):
    sessao = get_object_or_404(Sessao, pk=session_id)
    form = SessaoForm(request.POST, instance=sessao)
    if form.is_valid():
        form.save()
        messages.success(request, "Sessão atualizada com sucesso.")
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
def calendar_events(request):
    events = build_calendar_events()
    return JsonResponse(events, safe=False)


class CalendarDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/calendar.html"
