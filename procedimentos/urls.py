from django.urls import path

from .views.calendar import CalendarDashboardView, calendar_events
from .views.procedimentos import (
    ProcedimentoBulkScheduleView,
    ProcedimentoCreateView,
    ProcedimentoDeleteView,
    ProcedimentoDetailView,
    ProcedimentoListView,
    ProcedimentoUpdateView,
    TipoProcedimentoCreateView,
    TipoProcedimentoDeleteView,
    TipoProcedimentoListView,
    TipoProcedimentoUpdateView,
    toggle_procedimento_concluido,
)
from .views.sessoes import add_sessao, edit_sessao, update_status_sessao


urlpatterns = [
    path("procedimentos/", ProcedimentoListView.as_view(), name="procedure-list"),
    path("procedimentos/novo/", ProcedimentoCreateView.as_view(), name="procedure-create"),
    path("procedimentos/<int:pk>/", ProcedimentoDetailView.as_view(), name="procedure-detail"),
    path("procedimentos/<int:pk>/agendamento-lote/", ProcedimentoBulkScheduleView.as_view(), name="procedure-bulk-schedule"),
    path("procedimentos/<int:pk>/editar/", ProcedimentoUpdateView.as_view(), name="procedure-update"),
    path("procedimentos/<int:pk>/deletar/", ProcedimentoDeleteView.as_view(), name="procedure-delete"),
    path("procedimentos/<int:pk>/toggle-concluido/", toggle_procedimento_concluido, name="procedure-toggle-complete"),
    path("procedimentos/<int:pk>/sessoes/nova/", add_sessao, name="procedure-session-add"),
    path("sessoes/<int:session_id>/editar/", edit_sessao, name="procedure-session-edit"),
    path("sessoes/<int:session_id>/status/<slug:status>/", update_status_sessao, name="procedure-session-status"),
    path("tipos-procedimento/", TipoProcedimentoListView.as_view(), name="procedure-type-list"),
    path("tipos-procedimento/novo/", TipoProcedimentoCreateView.as_view(), name="procedure-type-create"),
    path("tipos-procedimento/<int:pk>/editar/", TipoProcedimentoUpdateView.as_view(), name="procedure-type-update"),
    path("tipos-procedimento/<int:pk>/deletar/", TipoProcedimentoDeleteView.as_view(), name="procedure-type-delete"),
    path("calendario/", CalendarDashboardView.as_view(), name="calendar-dashboard"),
    path("calendario/eventos/", calendar_events, name="calendar-events"),
]

