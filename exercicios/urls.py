from django.urls import path

from .views import (
    CategoriaExercicioCreateView,
    CategoriaExercicioDeleteView,
    CategoriaExercicioListView,
    CategoriaExercicioUpdateView,
    ExercicioCatalogoCreateView,
    ExercicioCatalogoDeleteView,
    ExercicioCatalogoListView,
    ExercicioCatalogoUpdateView,
    update_categoria_exercicio_color,
    update_sessao_exercicios,
)


urlpatterns = [
    path("exercicios/", ExercicioCatalogoListView.as_view(), name="exercise-list"),
    path("exercicios/novo/", ExercicioCatalogoCreateView.as_view(), name="exercise-create"),
    path("exercicios/<int:pk>/editar/", ExercicioCatalogoUpdateView.as_view(), name="exercise-update"),
    path("exercicios/<int:pk>/deletar/", ExercicioCatalogoDeleteView.as_view(), name="exercise-delete"),
    path("categorias-exercicios/", CategoriaExercicioListView.as_view(), name="exercise-category-list"),
    path("categorias-exercicios/nova/", CategoriaExercicioCreateView.as_view(), name="exercise-category-create"),
    path("categorias-exercicios/<int:pk>/editar/", CategoriaExercicioUpdateView.as_view(), name="exercise-category-update"),
    path("categorias-exercicios/<int:pk>/cor/", update_categoria_exercicio_color, name="exercise-category-color-update"),
    path("categorias-exercicios/<int:pk>/deletar/", CategoriaExercicioDeleteView.as_view(), name="exercise-category-delete"),
    path("sessoes/<int:session_id>/exercicios/", update_sessao_exercicios, name="session-exercise-update"),
]

