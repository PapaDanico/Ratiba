"""Immutable audit log writer.

The single ``record`` function is the only legal way to write rows into
``audit_events``. It must never read from or modify the table after insert.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent


def record(
    session: Session,
    *,
    operator_id: uuid.UUID,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append a single audit event. Caller is responsible for committing."""
    event = AuditEvent(
        operator_id=operator_id,
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
    )
    session.add(event)
    session.flush()
    return event
