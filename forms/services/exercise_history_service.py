"""Compatibility exports for the moved exercise history service."""

from exercicios.services.history import (
    STATUS_BLUE,
    STATUS_NORMAL,
    STATUS_RED,
    ExerciseHistoryStatus,
    SessionExerciseHistoryService,
)


__all__ = [
    "ExerciseHistoryStatus",
    "STATUS_BLUE",
    "STATUS_NORMAL",
    "STATUS_RED",
    "SessionExerciseHistoryService",
]
