from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, DetailView, FormView, ListView, UpdateView

from core.mixins import InternalPermissionMixin, SoftDeleteSuccessMessageMixin
from ..forms import ProcedimentoBulkScheduleForm, ProcedimentoForm, TipoProcedimentoForm
from ..models import Procedimento, TipoProcedimento
from ..selectors import (
    build_procedimento_detail_context,
    procedimento_detail_queryset,
    procedimento_list_queryset,
    tipo_procedimento_list_queryset,
)
from ..services.procedures import toggle_procedure_completion
from ..services.scheduling import generate_sessions_for_month_by_weekday
from .mixins import ProcedureCreateFlowMixin


class ProcedimentoListView(LoginRequiredMixin, ListView):
    model = Procedimento
    template_name = "forms/procedure_list.html"
    context_object_name = "procedimentos"
    paginate_by = 15

    def get_queryset(self):
        return procedimento_list_queryset(self.request)


class ProcedimentoDetailView(LoginRequiredMixin, DetailView):
    model = Procedimento
    template_name = "forms/procedure_detail.html"
    context_object_name = "procedimento"

    def get_queryset(self):
        return procedimento_detail_queryset()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_procedimento_detail_context(self.object))
        return context


class ProcedimentoCreateView(ProcedureCreateFlowMixin, LoginRequiredMixin, CreateView):
    model = Procedimento
    form_class = ProcedimentoForm
    template_name = "forms/procedure_form.html"
    success_url = reverse_lazy("procedure-list")

    def form_valid(self, form):
        response = self.handle_valid_procedure_form(form)
        if response is None:
            return self.form_invalid(form)
        return response


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


class ProcedimentoDeleteView(SoftDeleteSuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Procedimento
    template_name = "forms/procedure_confirm_delete.html"
    success_url = reverse_lazy("procedure-list")
    delete_success_message = "Procedimento removido com sucesso."


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
                timezone.localtime(conflict).strftime("%d/%m/%Y %H:%M") for conflict in result.skipped_conflicts
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
    toggle_procedure_completion(procedimento)
    estado = "concluído" if procedimento.concluido else "pendente"
    messages.success(request, f"Procedimento marcado como {estado}.")
    return redirect("procedure-detail", pk=procedimento.pk)


class TipoProcedimentoListView(InternalPermissionMixin, ListView):
    model = TipoProcedimento
    template_name = "forms/procedure_type_list.html"
    context_object_name = "tipos_procedimento"
    paginate_by = 15
    permission_required = "procedimentos.view_tipoprocedimento"

    def get_queryset(self):
        return tipo_procedimento_list_queryset(self.request)

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
    permission_required = "procedimentos.add_tipoprocedimento"

    def form_valid(self, form):
        messages.success(self.request, "Tipo de procedimento cadastrado com sucesso.")
        return super().form_valid(form)


class TipoProcedimentoUpdateView(InternalPermissionMixin, UpdateView):
    model = TipoProcedimento
    form_class = TipoProcedimentoForm
    template_name = "forms/procedure_type_form.html"
    success_url = reverse_lazy("procedure-type-list")
    permission_required = "procedimentos.change_tipoprocedimento"
    queryset = TipoProcedimento.all_objects.all()

    def form_valid(self, form):
        messages.success(self.request, "Tipo de procedimento atualizado com sucesso.")
        return super().form_valid(form)


class TipoProcedimentoDeleteView(SoftDeleteSuccessMessageMixin, InternalPermissionMixin, DeleteView):
    model = TipoProcedimento
    template_name = "forms/procedure_type_confirm_delete.html"
    success_url = reverse_lazy("procedure-type-list")
    permission_required = "procedimentos.delete_tipoprocedimento"
    queryset = TipoProcedimento.all_objects.all()
    delete_success_message = "Tipo de procedimento desativado com sucesso."
