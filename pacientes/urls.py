from django.urls import path

from .views import (
    PacienteCreateView,
    PacienteDeleteView,
    PacienteDetailView,
    PacienteListView,
    PacienteUpdateView,
    get_paciente_data,
    mark_paciente_exercise_day,
    update_paciente_exercise_note,
)


urlpatterns = [
    path("api/paciente/<int:paciente_id>/", get_paciente_data, name="api-paciente-data"),
    path("inscricao/", PacienteListView.as_view(), name="inscricao-list"),
    path("inscricao/nova/", PacienteCreateView.as_view(), name="inscricao-create"),
    path("inscricao/<int:pk>/", PacienteDetailView.as_view(), name="inscricao-detail"),
    path(
        "inscricao/<int:pk>/exercicios/marcar-dia/",
        mark_paciente_exercise_day,
        name="patient-exercise-day-mark",
    ),
    path(
        "inscricao/<int:pk>/exercicios/nota/",
        update_paciente_exercise_note,
        name="patient-exercise-note-update",
    ),
    path("inscricao/<int:pk>/editar/", PacienteUpdateView.as_view(), name="inscricao-update"),
    path("inscricao/<int:pk>/deletar/", PacienteDeleteView.as_view(), name="inscricao-delete"),
]
