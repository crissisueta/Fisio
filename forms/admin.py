"""Load admin registrations split by domain."""

from avaliacoes import admin as avaliacoes_admin
from exercicios import admin as exercicios_admin
from pacientes import admin as pacientes_admin
from procedimentos import admin as procedimentos_admin


__all__ = [
    "avaliacoes_admin",
    "exercicios_admin",
    "pacientes_admin",
    "procedimentos_admin",
]
