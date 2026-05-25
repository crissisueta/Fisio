"""Compatibility exports for legacy `forms.models` imports."""

from avaliacoes.models import Avaliacao, TipoAvaliacao
from core.models import (
    ActiveManager,
    AllObjectsManager,
    SoftDeleteModel,
    SoftDeleteQuerySet,
    TimestampedModel,
)
from exercicios.models import (
    CategoriaExercicio,
    ExercicioCatalogo,
    FichaExercicios,
    ProcedimentoExercicio,
    SessaoExercicio,
)
from pacientes.models import Paciente
from procedimentos.models import Procedimento, Sessao, TipoProcedimento


__all__ = [
    "ActiveManager",
    "AllObjectsManager",
    "Avaliacao",
    "CategoriaExercicio",
    "ExercicioCatalogo",
    "FichaExercicios",
    "Paciente",
    "Procedimento",
    "ProcedimentoExercicio",
    "Sessao",
    "SessaoExercicio",
    "SoftDeleteModel",
    "SoftDeleteQuerySet",
    "TimestampedModel",
    "TipoAvaliacao",
    "TipoProcedimento",
]
