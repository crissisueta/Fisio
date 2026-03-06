from django.urls import path

from .views import (
    AvaliacaoCreateView,
    AvaliacaoDeleteView,
    AvaliacaoDetailView,
    AvaliacaoListView,
    AvaliacaoUpdateView,
    CalendarDashboardView,
    PacienteCreateView,
    PacienteDeleteView,
    PacienteDetailView,
    PacienteListView,
    PacienteUpdateView,
    ProcedimentoCreateView,
    ProcedimentoDeleteView,
    ProcedimentoDetailView,
    ProcedimentoListView,
    ProcedimentoUpdateView,
    add_sessao,
    calendar_events,
    edit_sessao,
    get_paciente_data,
    toggle_procedimento_concluido,
    update_status_sessao,
)


urlpatterns = [
    path("api/paciente/<int:paciente_id>/", get_paciente_data, name="api-paciente-data"),

    path("inscricao/", PacienteListView.as_view(), name="inscricao-list"),
    path("inscricao/nova/", PacienteCreateView.as_view(), name="inscricao-create"),
    path("inscricao/<int:pk>/", PacienteDetailView.as_view(), name="inscricao-detail"),
    path("inscricao/<int:pk>/editar/", PacienteUpdateView.as_view(), name="inscricao-update"),
    path("inscricao/<int:pk>/deletar/", PacienteDeleteView.as_view(), name="inscricao-delete"),

    path("avaliacoes/", AvaliacaoListView.as_view(), name="avaliacao-list"),
    path("avaliacoes/nova/", AvaliacaoCreateView.as_view(), name="avaliacao-create"),
    path("avaliacoes/<int:pk>/", AvaliacaoDetailView.as_view(), name="avaliacao-detail"),
    path("avaliacoes/<int:pk>/editar/", AvaliacaoUpdateView.as_view(), name="avaliacao-update"),
    path("avaliacoes/<int:pk>/deletar/", AvaliacaoDeleteView.as_view(), name="avaliacao-delete"),

    path("procedimentos/", ProcedimentoListView.as_view(), name="procedure-list"),
    path("procedimentos/novo/", ProcedimentoCreateView.as_view(), name="procedure-create"),
    path("procedimentos/<int:pk>/", ProcedimentoDetailView.as_view(), name="procedure-detail"),
    path("procedimentos/<int:pk>/editar/", ProcedimentoUpdateView.as_view(), name="procedure-update"),
    path("procedimentos/<int:pk>/deletar/", ProcedimentoDeleteView.as_view(), name="procedure-delete"),
    path("procedimentos/<int:pk>/toggle-concluido/", toggle_procedimento_concluido, name="procedure-toggle-complete"),

    path("procedimentos/<int:pk>/sessoes/nova/", add_sessao, name="procedure-session-add"),
    path("sessoes/<int:session_id>/editar/", edit_sessao, name="procedure-session-edit"),
    path("sessoes/<int:session_id>/status/<slug:status>/", update_status_sessao, name="procedure-session-status"),

    path("calendario/", CalendarDashboardView.as_view(), name="calendar-dashboard"),
    path("calendario/eventos/", calendar_events, name="calendar-events"),
]
