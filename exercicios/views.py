import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from core.mixins import InternalPermissionMixin, SoftDeleteSuccessMessageMixin
from core.models import ActivityLog
from core.services.activity import log_activity
from procedimentos.models import Sessao
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


@login_required
@require_POST
def update_categoria_exercicio_color(request, pk):
    categoria = get_object_or_404(CategoriaExercicio.all_objects, pk=pk)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
        if not isinstance(payload, dict):
            raise ValueError
        color = str(payload.get("color") or "").strip().upper()
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"success": False, "error": "Informe uma cor válida."}, status=400)

    categoria.cor = color
    try:
        categoria.full_clean()
    except ValidationError as exc:
        return JsonResponse({"success": False, "error": _validation_error_text(exc)}, status=400)

    categoria.save(update_fields=["cor"])
    log_activity(
        user=request.user,
        event_type="admin.exercise_category.color_updated",
        message=f"alterou a cor da categoria de exercício {categoria.nome}",
        level=ActivityLog.LEVEL_INFO,
        metadata={"exercise_category_id": categoria.pk, "color": categoria.cor},
    )
    return JsonResponse({"success": True, "category_id": categoria.pk, "color": categoria.cor})


def _validation_error_text(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(message for messages in exc.message_dict.values() for message in messages)
    return " ".join(exc.messages)


class CategoriaExercicioListView(InternalPermissionMixin, ListView):
    model = CategoriaExercicio
    template_name = "forms/exercise_category_list.html"
    context_object_name = "categorias"
    paginate_by = 15
    permission_required = "exercicios.view_categoriaexercicio"

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
    permission_required = "exercicios.add_categoriaexercicio"

    def form_valid(self, form):
        messages.success(self.request, "Categoria de exercício cadastrada com sucesso.")
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="admin.exercise_category.created",
            message=f"cadastrou categoria de exercício {self.object.nome}",
            level=ActivityLog.LEVEL_SUCCESS,
            metadata={"exercise_category_id": self.object.pk},
        )
        return response


class CategoriaExercicioUpdateView(InternalPermissionMixin, UpdateView):
    model = CategoriaExercicio
    form_class = CategoriaExercicioForm
    template_name = "forms/exercise_category_form.html"
    success_url = reverse_lazy("exercise-category-list")
    permission_required = "exercicios.change_categoriaexercicio"
    queryset = CategoriaExercicio.all_objects.all()

    def form_valid(self, form):
        messages.success(self.request, "Categoria de exercício atualizada com sucesso.")
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="admin.exercise_category.updated",
            message=f"atualizou categoria de exercício {self.object.nome}",
            level=ActivityLog.LEVEL_INFO,
            metadata={"exercise_category_id": self.object.pk},
        )
        return response


class CategoriaExercicioDeleteView(SoftDeleteSuccessMessageMixin, InternalPermissionMixin, DeleteView):
    model = CategoriaExercicio
    template_name = "forms/exercise_category_confirm_delete.html"
    success_url = reverse_lazy("exercise-category-list")
    permission_required = "exercicios.delete_categoriaexercicio"
    queryset = CategoriaExercicio.all_objects.all()
    delete_success_message = "Categoria de exercício desativada com sucesso."

    def form_valid(self, form):
        category_id = self.object.pk
        category_name = self.object.nome
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="admin.exercise_category.deleted",
            message=f"desativou categoria de exercício {category_name}",
            level=ActivityLog.LEVEL_WARNING,
            metadata={"exercise_category_id": category_id},
        )
        return response


class ExercicioCatalogoListView(InternalPermissionMixin, ListView):
    model = ExercicioCatalogo
    template_name = "forms/exercise_list.html"
    context_object_name = "exercicios"
    paginate_by = 15
    permission_required = "exercicios.view_exerciciocatalogo"

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
    permission_required = "exercicios.add_exerciciocatalogo"

    def form_valid(self, form):
        messages.success(self.request, "Exercício cadastrado com sucesso.")
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="admin.exercise.created",
            message=f"cadastrou exercício {self.object.nome}",
            level=ActivityLog.LEVEL_SUCCESS,
            metadata={"exercise_id": self.object.pk, "exercise_category_id": self.object.categoria_id},
        )
        return response


class ExercicioCatalogoUpdateView(InternalPermissionMixin, UpdateView):
    model = ExercicioCatalogo
    form_class = ExercicioCatalogoForm
    template_name = "forms/exercise_form.html"
    success_url = reverse_lazy("exercise-list")
    permission_required = "exercicios.change_exerciciocatalogo"
    queryset = ExercicioCatalogo.all_objects.select_related("categoria")

    def form_valid(self, form):
        messages.success(self.request, "Exercício atualizado com sucesso.")
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="admin.exercise.updated",
            message=f"atualizou exercício {self.object.nome}",
            level=ActivityLog.LEVEL_INFO,
            metadata={"exercise_id": self.object.pk, "exercise_category_id": self.object.categoria_id},
        )
        return response


class ExercicioCatalogoDeleteView(SoftDeleteSuccessMessageMixin, InternalPermissionMixin, DeleteView):
    model = ExercicioCatalogo
    template_name = "forms/exercise_confirm_delete.html"
    success_url = reverse_lazy("exercise-list")
    permission_required = "exercicios.delete_exerciciocatalogo"
    queryset = ExercicioCatalogo.all_objects.select_related("categoria")
    delete_success_message = "Exercício desativado com sucesso."

    def form_valid(self, form):
        exercise_id = self.object.pk
        exercise_name = self.object.nome
        category_id = self.object.categoria_id
        response = super().form_valid(form)
        log_activity(
            user=self.request.user,
            event_type="admin.exercise.deleted",
            message=f"desativou exercício {exercise_name}",
            level=ActivityLog.LEVEL_WARNING,
            metadata={"exercise_id": exercise_id, "exercise_category_id": category_id},
        )
        return response

