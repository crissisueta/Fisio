from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..core.mixins import SoftDeleteSuccessMessageMixin
from .forms import AvaliacaoForm
from .models import Avaliacao
from .selectors import avaliacao_list_queryset


class AvaliacaoListView(LoginRequiredMixin, ListView):
    model = Avaliacao
    template_name = "forms/avaliacao_list.html"
    context_object_name = "avaliacoes"
    paginate_by = 15

    def get_queryset(self):
        return avaliacao_list_queryset()


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


class AvaliacaoDeleteView(SoftDeleteSuccessMessageMixin, LoginRequiredMixin, DeleteView):
    model = Avaliacao
    template_name = "forms/avaliacao_confirm_delete.html"
    success_url = reverse_lazy("avaliacao-list")
    delete_success_message = "Avaliação removida com sucesso."

