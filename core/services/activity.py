import logging
from collections.abc import Mapping
from typing import Any

from django.db import transaction

from core.models import ActivityLog


logger = logging.getLogger(__name__)

_SENSITIVE_KEY_PARTS = (
    "password",
    "senha",
    "token",
    "secret",
    "cookie",
    "session",
    "trace",
    "stack",
    "raw",
)


def actor_display_name(user) -> str:
    if not user or not getattr(user, "is_authenticated", False):
        return "Sistema"
    full_name = user.get_full_name().strip()
    return full_name or user.get_username() or "Usuario"


def log_activity(
    *,
    user=None,
    event_type: str,
    message: str,
    level: str = ActivityLog.LEVEL_INFO,
    metadata: Mapping[str, Any] | None = None,
) -> ActivityLog | None:
    """Cria um registro de atividade sem interromper a ação principal."""

    try:
        valid_levels = {choice[0] for choice in ActivityLog.LEVEL_CHOICES}
        with transaction.atomic():
            return ActivityLog.objects.create(
                user=user if user and getattr(user, "is_authenticated", False) else None,
                event_type=(event_type or "system.event")[:100],
                message=(message or "Atividade registrada")[:500],
                level=level if level in valid_levels else ActivityLog.LEVEL_INFO,
                metadata=_safe_metadata(metadata),
            )
    except Exception:
        logger.exception("Failed to create activity log entry.")
        return None


def _safe_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}

    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key_text = str(key)[:100]
        lowered = key_text.lower()
        if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
            safe[key_text] = "[redacted]"
        else:
            safe[key_text] = _json_safe_value(value)
    return safe


def _json_safe_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe_value(item) for item in value[:50]]
    if isinstance(value, Mapping):
        return _safe_metadata(value)
    return str(value)[:200]
