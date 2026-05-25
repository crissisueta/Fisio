"""Compatibility exports for the moved scheduling service."""

from procedimentos.services.scheduling import (
    BulkSessionGenerationResult,
    ScheduleConflict,
    WEEKDAY_CHOICES,
    WEEKDAY_LABELS,
    create_initial_session_for_procedure,
    create_session_for_procedimento,
    ensure_aware_datetime,
    find_schedule_conflict,
    generate_sessions_for_month_by_weekday,
    get_session_end_datetime,
    resequence_sessoes,
    update_sessao,
    validate_session_conflict,
)


__all__ = [
    "BulkSessionGenerationResult",
    "ScheduleConflict",
    "WEEKDAY_CHOICES",
    "WEEKDAY_LABELS",
    "create_initial_session_for_procedure",
    "create_session_for_procedimento",
    "ensure_aware_datetime",
    "find_schedule_conflict",
    "generate_sessions_for_month_by_weekday",
    "get_session_end_datetime",
    "resequence_sessoes",
    "update_sessao",
    "validate_session_conflict",
]
