from __future__ import annotations

from contextvars import ContextVar

current_actor_user_id: ContextVar[str | None] = ContextVar(
    "current_actor_user_id",
    default=None,
)


def set_current_actor(user_id: str | None) -> None:
    """Set the current actor for audit hooks and audit service helpers."""
    current_actor_user_id.set(user_id)


def get_current_actor() -> str | None:
    """Return the current actor user ID (as string), or None if not set."""
    return current_actor_user_id.get()
