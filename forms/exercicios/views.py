from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from ..core.mixins import InternalPermissionMixin, SoftDeleteSuccessMessageMixin
from ..procedimentos.models import Sessao
from .forms import CategoriaExercicioForm, ExercicioCatalogoForm, SessaoExercicioSelectionForm
from .models import CategoriaExercicio, ExercicioCatalogo
from .selectors import categoria_exercicio_list_queryset, categorias_disponiveis_queryset, exercicio_catalogo_list_queryset
from .services.session_assignment import assign_exercises_to_session, get_default_exercise_ids_for_session


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

    fallback_ids = get_default_exercise_ids_for_session(sessao)
    form = SessaoExercicioSelectionForm(request.POST, sessao=sessao, selected_ids=fallback_ids)
    if not form.is_valid():
        messages.error(request, "Não foi possível atualizar os exercícios da sessão.")
        return redirect("procedure-detail", pk=procedimento.pk)

    assign_exercises_to_session(sessao, list(form.cleaned_data["exercicios"]))
    messages.success(request, f"Exercícios da sessão {sessao.numero or '-'} atualizados com sucesso.")
    return redirect(f"{reverse('procedure-detail', kwargs={'pk': procedimento.pk})}#sessao-{sessao.pk}")


class CategoriaExercicioListView(InternalPermissionMixin, ListView):
    model = CategoriaExercicio
    template_name = "forms/exercise_category_list.html"
    context_object_name = "categorias"
    paginate_by = 15
    permission_required = "forms.view_categoriaexercicio"

    def get_queryset(self):
        return categoria_exercicio_list_queryset(self.request)

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


class CategoriaExercicioDeleteView(SoftDeleteSuccessMessageMixin, InternalPermissionMixin, DeleteView):
    model = CategoriaExercicio
    template_name = "forms/exercise_category_confirm_delete.html"
    success_url = reverse_lazy("exercise-category-list")
    permission_required = "forms.delete_categoriaexercicio"
    queryset = CategoriaExercicio.all_objects.all()
    delete_success_message = "Categoria de exercício desativada com sucesso."


class ExercicioCatalogoListView(InternalPermissionMixin, ListView):
    model = ExercicioCatalogo
    template_name = "forms/exercise_list.html"
    context_object_name = "exercicios"
    paginate_by = 15
    permission_required = "forms.view_exerciciocatalogo"

    def get_queryset(self):
        return exercicio_catalogo_list_queryset(self.request)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["selected_category"] = self.request.GET.get("categoria", "").strip()
        context["status_filter"] = self.request.GET.get("status", "ativos")
        context["categorias_disponiveis"] = categorias_disponiveis_queryset()
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


class ExercicioCatalogoDeleteView(SoftDeleteSuccessMessageMixin, InternalPermissionMixin, DeleteView):
    model = ExercicioCatalogo
    template_name = "forms/exercise_confirm_delete.html"
    success_url = reverse_lazy("exercise-list")
    permission_required = "forms.delete_exerciciocatalogo"
    queryset = ExercicioCatalogo.all_objects.select_related("categoria")
    delete_success_message = "Exercício desativado com sucesso."

