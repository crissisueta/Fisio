"""Compatibility exports for legacy `forms.views` imports."""

from .avaliacoes.views import (
    AvaliacaoCreateView,
    AvaliacaoDeleteView,
    AvaliacaoDetailView,
    AvaliacaoListView,
    AvaliacaoUpdateView,
)
from .core.mixins import InternalPermissionMixin
from .exercicios.views import (
    CategoriaExercicioCreateView,
    CategoriaExercicioDeleteView,
    CategoriaExercicioListView,
    CategoriaExercicioUpdateView,
    ExercicioCatalogoCreateView,
    ExercicioCatalogoDeleteView,
    ExercicioCatalogoListView,
    ExercicioCatalogoUpdateView,
    update_sessao_exercicios,
)
from .pacientes.views import (
    PacienteCreateView,
    PacienteDeleteView,
    PacienteDetailView,
    PacienteListView,
    PacienteUpdateView,
    get_paciente_data,
)
from .painel.views import DashboardView
from .procedimentos.views.calendar import CalendarDashboardView, calendar_events
from .procedimentos.views.mixins import ProcedureCreateFlowMixin
from .procedimentos.views.procedimentos import (
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
from .procedimentos.views.sessoes import add_sessao, edit_sessao, update_status_sessao


__all__ = [
    "AvaliacaoCreateView",
    "AvaliacaoDeleteView",
    "AvaliacaoDetailView",
    "AvaliacaoListView",
    "AvaliacaoUpdateView",
    "CalendarDashboardView",
    "CategoriaExercicioCreateView",
    "CategoriaExercicioDeleteView",
    "CategoriaExercicioListView",
    "CategoriaExercicioUpdateView",
    "DashboardView",
    "ExercicioCatalogoCreateView",
    "ExercicioCatalogoDeleteView",
    "ExercicioCatalogoListView",
    "ExercicioCatalogoUpdateView",
    "InternalPermissionMixin",
    "PacienteCreateView",
    "PacienteDeleteView",
    "PacienteDetailView",
    "PacienteListView",
    "PacienteUpdateView",
    "ProcedimentoBulkScheduleView",
    "ProcedimentoCreateView",
    "ProcedimentoDeleteView",
    "ProcedimentoDetailView",
    "ProcedimentoListView",
    "ProcedimentoUpdateView",
    "ProcedureCreateFlowMixin",
    "TipoProcedimentoCreateView",
    "TipoProcedimentoDeleteView",
    "TipoProcedimentoListView",
    "TipoProcedimentoUpdateView",
    "add_sessao",
    "calendar_events",
    "edit_sessao",
    "get_paciente_data",
    "toggle_procedimento_concluido",
    "update_sessao_exercicios",
    "update_status_sessao",
]
