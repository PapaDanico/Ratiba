"""RBAC — staff write actions require a writer role; reads stay open.

The decorator-level ``require_writer`` dependency gates mutating endpoints to
CREWING_OFFICER / CHIEF_PILOT / ADMIN. A (future) restricted PILOT *user* role
can read but not mutate. All current logins are crewing officers, so this is
future-proofing + the OWASP access-control item from the security audit.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import User
from app.models.user import UserRole


def _pilot_role_headers(db_session: Session, operator_id) -> dict[str, str]:
    pilot_user = User(
        operator_id=operator_id,
        email="pilotrole@test.example",
        hashed_password=hash_password("hunter2pass"),
        full_name="Pilot Role User",
        role=UserRole.PILOT,
        is_active=True,
    )
    db_session.add(pilot_user)
    db_session.commit()
    db_session.refresh(pilot_user)
    token = create_access_token(str(pilot_user.id), extra={"operator_id": str(operator_id)})
    return {"Authorization": f"Bearer {token}"}


def test_non_writer_role_blocked_from_mutations(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, officer = auth_client
    pilot_headers = _pilot_role_headers(db_session, officer.operator_id)
    body = {"registration": "5Y-RBAC", "aircraft_type": "F50", "active": True}

    # Writer (the seeded crewing officer) passes the role gate.
    allowed = client.post("/api/v1/fleet", json=body)
    assert allowed.status_code != 403, allowed.text

    # Non-writer (PILOT-role user) is forbidden from the write.
    denied = client.post("/api/v1/fleet", json=body, headers=pilot_headers)
    assert denied.status_code == 403, denied.text


def test_non_writer_role_can_still_read(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, officer = auth_client
    pilot_headers = _pilot_role_headers(db_session, officer.operator_id)
    # Reads remain open to any authenticated staff user.
    read = client.get("/api/v1/fleet", headers=pilot_headers)
    assert read.status_code == 200, read.text
