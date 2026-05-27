"""Audit log writer — Phase 1 infrastructure.

``audit_log.record`` is the only legal path that any future write must take.
This test pins its behaviour without touching a database (the
``audit_events`` table relies on PostgreSQL JSONB and an append-only
trigger, so a live integration test belongs in CI against the PG service).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.services.audit_log import record


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.flush_count: int = 0

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flush_count += 1


def test_record_builds_an_audit_event_with_supplied_fields() -> None:
    session = _FakeSession()
    operator_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    entity_id = uuid.uuid4()

    event = record(
        session,  # type: ignore[arg-type]
        operator_id=operator_id,
        actor_user_id=actor_id,
        action="CREATE_FDP",
        entity_type="flight_duty_period",
        entity_id=entity_id,
        before_state=None,
        after_state={"duty_hours": 10.0},
    )

    assert session.added == [event]
    assert session.flush_count == 1
    assert event.operator_id == operator_id
    assert event.actor_user_id == actor_id
    assert event.action == "CREATE_FDP"
    assert event.entity_type == "flight_duty_period"
    assert event.entity_id == entity_id
    assert event.before_state is None
    assert event.after_state == {"duty_hours": 10.0}


def test_record_carries_before_and_after_states() -> None:
    session = _FakeSession()
    event = record(
        session,  # type: ignore[arg-type]
        operator_id=uuid.uuid4(),
        actor_user_id=None,
        action="UPDATE_FDP",
        entity_type="flight_duty_period",
        entity_id=uuid.uuid4(),
        before_state={"duty_hours": 8.0},
        after_state={"duty_hours": 10.0},
    )
    assert event.before_state == {"duty_hours": 8.0}
    assert event.after_state == {"duty_hours": 10.0}
    assert event.actor_user_id is None
