from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from .forms import FichaInscricaoForm, ProcedureForm, ProcedureSessionForm
from .models import FichaInscricao, Procedure, ProcedureSession
from .services.calendar_service import build_calendar_events


def _session_datetime_aware(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["inscricoes_count"] = FichaInscricao.objects.count()
        context["procedures_count"] = Procedure.objects.count()
        context["sessions_count"] = ProcedureSession.objects.count()
        context["completed_procedures_count"] = Procedure.objects.filter(is_complete=True).count()
        context["pending_procedures_count"] = Procedure.objects.filter(is_complete=False).count()
        return context


@login_required
def get_paciente_data(request, paciente_id):
    """API endpoint para retornar dados do paciente em JSON."""
    paciente = get_object_or_404(FichaInscricao, pk=paciente_id)
    return JsonResponse(
        {
            "nome": paciente.nome,
            "profissao": paciente.profissao,
            "data_nascimento": paciente.data_nascimento.isoformat(),
            "endereco": paciente.endereco,
            "telefone": paciente.telefone,
            "celular": paciente.celular,
            "idade": (timezone.now().date() - paciente.data_nascimento).days // 365,
            "procedures_count": paciente.procedures.count(),
        }
    )


class FichaInscricaoListView(LoginRequiredMixin, ListView):
    model = FichaInscricao
    template_name = "forms/inscricao_list.html"
    context_object_name = "fichas"
    paginate_by = 10


class FichaInscricaoDetailView(LoginRequiredMixin, DetailView):
    model = FichaInscricao
    template_name = "forms/inscricao_detail.html"
    context_object_name = "ficha"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["procedures"] = (
            self.object.procedures.select_related("procedure_type")
            .prefetch_related("sessions")
            .order_by("-created_at")
        )
        return context


class FichaInscricaoCreateView(LoginRequiredMixin, CreateView):
    model = FichaInscricao
    form_class = FichaInscricaoForm
    template_name = "forms/inscricao_form.html"
    success_url = reverse_lazy("inscricao-list")

    def form_valid(self, form):
        messages.success(self.request, "Ficha de Inscrição criada com sucesso!")
        return super().form_valid(form)


class FichaInscricaoUpdateView(LoginRequiredMixin, UpdateView):
    model = FichaInscricao
    form_class = FichaInscricaoForm
    template_name = "forms/inscricao_form.html"
    success_url = reverse_lazy("inscricao-list")

    def form_valid(self, form):
        messages.success(self.request, "Ficha de Inscrição atualizada com sucesso!")
        return super().form_valid(form)


class FichaInscricaoDeleteView(LoginRequiredMixin, DeleteView):
    model = FichaInscricao
    template_name = "forms/inscricao_confirm_delete.html"
    success_url = reverse_lazy("inscricao-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Ficha de Inscrição deletada com sucesso!")
        return super().delete(request, *args, **kwargs)


class ProcedureListView(LoginRequiredMixin, ListView):
    model = Procedure
    template_name = "forms/procedure_list.html"
    context_object_name = "procedures"
    paginate_by = 15

    def get_queryset(self):
        queryset = Procedure.objects.select_related("patient", "procedure_type").order_by("-created_at")

        patient_id = self.request.GET.get("patient")
        type_id = self.request.GET.get("type")

        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)
        if type_id:
            queryset = queryset.filter(procedure_type_id=type_id)

        return queryset


class ProcedureDetailView(LoginRequiredMixin, DetailView):
    model = Procedure
    template_name = "forms/procedure_detail.html"
    context_object_name = "procedure"

    def get_queryset(self):
        return Procedure.objects.select_related("patient", "procedure_type").prefetch_related("sessions")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_sessions = list(self.object.sessions.order_by("scheduled_datetime"))
        now = timezone.now()

        upcoming_sessions = [
            sess for sess in all_sessions
            if _session_datetime_aware(sess.scheduled_datetime) >= now
            and sess.status in [ProcedureSession.STATUS_SCHEDULED]
        ]
        past_sessions = [sess for sess in all_sessions if sess not in upcoming_sessions]

        context["next_upcoming_session"] = upcoming_sessions[0] if upcoming_sessions else None
        context["upcoming_sessions"] = upcoming_sessions
        context["past_sessions"] = past_sessions
        context["session_form"] = ProcedureSessionForm()
        return context


class ProcedureCreateView(LoginRequiredMixin, CreateView):
    model = Procedure
    form_class = ProcedureForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

    def form_valid(self, form):
        messages.success(self.request, "Procedimento criado com sucesso!")
        return super().form_valid(form)


class ProcedureUpdateView(LoginRequiredMixin, UpdateView):
    model = Procedure
    form_class = ProcedureForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

    def form_valid(self, form):
        messages.success(self.request, "Procedimento atualizado com sucesso!")
        return super().form_valid(form)


class ProcedureDeleteView(LoginRequiredMixin, DeleteView):
    model = Procedure
    template_name = "forms/procedure_confirm_delete.html"
    success_url = reverse_lazy("procedure-list")

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Procedimento deletado com sucesso!")
        return super().delete(request, *args, **kwargs)


@login_required
@require_POST
def toggle_procedure_complete(request, pk):
    procedure = get_object_or_404(Procedure, pk=pk)
    procedure.is_complete = not procedure.is_complete
    procedure.save(update_fields=["is_complete", "updated_at"])
    status = "concluído" if procedure.is_complete else "pendente"
    messages.success(request, f"Procedimento marcado como {status}.")
    return redirect("procedure-detail", pk=procedure.pk)


@login_required
@require_POST
def add_procedure_session(request, pk):
    procedure = get_object_or_404(Procedure, pk=pk)
    form = ProcedureSessionForm(request.POST)

    if form.is_valid():
        session = form.save(commit=False)
        session.procedure = procedure
        session.save()
        messages.success(request, "Sessão adicionada com sucesso!")
    else:
        messages.error(request, "Não foi possível adicionar a sessão. Verifique os dados informados.")

    return redirect("procedure-detail", pk=procedure.pk)


@login_required
@require_POST
def edit_procedure_session(request, session_id):
    session = get_object_or_404(ProcedureSession, pk=session_id)
    form = ProcedureSessionForm(request.POST, instance=session)

    if form.is_valid():
        form.save()
        messages.success(request, "Sessão atualizada com sucesso!")
    else:
        messages.error(request, "Não foi possível atualizar a sessão.")

    return redirect("procedure-detail", pk=session.procedure_id)


@login_required
@require_POST
def update_procedure_session_status(request, session_id, status):
    session = get_object_or_404(ProcedureSession, pk=session_id)
    allowed_statuses = {choice[0] for choice in ProcedureSession.STATUS_CHOICES}
    if status not in allowed_statuses:
        messages.error(request, "Status de sessão inválido.")
        return redirect("procedure-detail", pk=session.procedure_id)

    session.status = status
    session.save(update_fields=["status", "completed", "updated_at"])
    messages.success(request, "Status da sessão atualizado com sucesso.")
    return redirect("procedure-detail", pk=session.procedure_id)


@login_required
def calendar_events(request):
    events = build_calendar_events()
    return JsonResponse(events, safe=False)


class CalendarDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/calendar.html"
