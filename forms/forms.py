"""Compatibility exports for legacy `forms.forms` imports."""

from .avaliacoes.forms import AvaliacaoForm
from .exercicios.forms import CategoriaExercicioForm, ExercicioCatalogoForm, SessaoExercicioSelectionForm
from .pacientes.forms import PacienteForm
from .procedimentos.forms import (
    ProcedimentoBulkScheduleForm,
    ProcedimentoForm,
    SessaoForm,
    TipoProcedimentoForm,
)


__all__ = [
    "AvaliacaoForm",
    "CategoriaExercicioForm",
    "ExercicioCatalogoForm",
    "PacienteForm",
    "ProcedimentoBulkScheduleForm",
    "ProcedimentoForm",
    "SessaoExercicioSelectionForm",
    "SessaoForm",
    "TipoProcedimentoForm",
]
