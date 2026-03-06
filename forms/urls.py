from django.urls import path

from .views import (
    CalendarDashboardView,
    FichaInscricaoCreateView,
    FichaInscricaoDeleteView,
    FichaInscricaoDetailView,
    FichaInscricaoListView,
    FichaInscricaoUpdateView,
    ProcedureCreateView,
    ProcedureDeleteView,
    ProcedureDetailView,
    ProcedureListView,
    ProcedureUpdateView,
    add_procedure_session,
    calendar_events,
    edit_procedure_session,
    get_paciente_data,
    toggle_procedure_complete,
    update_procedure_session_status,
)


urlpatterns = [
    path("api/paciente/<int:paciente_id>/", get_paciente_data, name="api-paciente-data"),
    path("inscricao/", FichaInscricaoListView.as_view(), name="inscricao-list"),
    path("inscricao/nova/", FichaInscricaoCreateView.as_view(), name="inscricao-create"),
    path("inscricao/<int:pk>/", FichaInscricaoDetailView.as_view(), name="inscricao-detail"),
    path("inscricao/<int:pk>/editar/", FichaInscricaoUpdateView.as_view(), name="inscricao-update"),
    path("inscricao/<int:pk>/deletar/", FichaInscricaoDeleteView.as_view(), name="inscricao-delete"),
    path("procedures/", ProcedureListView.as_view(), name="procedure-list"),
    path("procedures/novo/", ProcedureCreateView.as_view(), name="procedure-create"),
    path("procedures/<int:pk>/", ProcedureDetailView.as_view(), name="procedure-detail"),
    path("procedures/<int:pk>/editar/", ProcedureUpdateView.as_view(), name="procedure-update"),
    path("procedures/<int:pk>/deletar/", ProcedureDeleteView.as_view(), name="procedure-delete"),
    path("procedures/<int:pk>/toggle-complete/", toggle_procedure_complete, name="procedure-toggle-complete"),
    path("procedures/<int:pk>/sessions/new/", add_procedure_session, name="procedure-session-add"),
    path("sessions/<int:session_id>/edit/", edit_procedure_session, name="procedure-session-edit"),
    path(
        "sessions/<int:session_id>/status/<slug:status>/",
        update_procedure_session_status,
        name="procedure-session-status",
    ),
    path("calendar/", CalendarDashboardView.as_view(), name="calendar-dashboard"),
    path("calendar/events/", calendar_events, name="calendar-events"),
]
