from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..core.mixins import SoftDeleteSuccessMessageMixin
from .forms import PacienteForm
from .models import Paciente
from .selectors import get_paciente_detail_context, serialize_paciente_summary


@login_required
def get_paciente_data(request, paciente_id):
    paciente = get_object_or_404(Paciente, pk=paciente_id)
    return JsonResponse(serialize_paciente_summary(paciente))


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
        context.update(get_paciente_detail_context(self.object))
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


class PacienteDeleteView(SoftDeleteSuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Paciente
    template_name = "forms/inscricao_confirm_delete.html"
    success_url = reverse_lazy("inscricao-list")
    delete_success_message = "Paciente removido com sucesso."

