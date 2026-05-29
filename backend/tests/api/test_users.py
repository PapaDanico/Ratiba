"""Team / user-management endpoints (operator-admin surface)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.models.user import UserRole


def _make_admin(db: Session, user: User) -> None:
    user.role = UserRole.ADMIN
    db.commit()


def test_non_admin_cannot_manage_users(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    # seeded_user is a CREWING_OFFICER — a writer, but not an admin.
    assert user.role is UserRole.CREWING_OFFICER
    assert client.get("/api/v1/users").status_code == 403
    assert (
        client.post(
            "/api/v1/users",
            json={
                "email": "new@test.example",
                "full_name": "New Officer",
                "role": "CREWING_OFFICER",
                "password": "hunter2pass",
            },
        ).status_code
        == 403
    )


def test_admin_creates_and_lists_users(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _make_admin(db_session, user)

    resp = client.post(
        "/api/v1/users",
        json={
            "email": "chief@test.example",
            "full_name": "Chief Pilot",
            "role": "CHIEF_PILOT",
            "password": "hunter2pass",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "chief@test.example"
    assert body["role"] == "CHIEF_PILOT"
    assert body["is_active"] is True

    listing = client.get("/api/v1/users")
    assert listing.status_code == 200
    emails = {u["email"] for u in listing.json()}
    assert {"officer@test.example", "chief@test.example"} <= emails


def test_create_user_rejects_duplicate_email(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _make_admin(db_session, user)
    resp = client.post(
        "/api/v1/users",
        json={
            "email": user.email,  # already exists
            "full_name": "Clone",
            "role": "CREWING_OFFICER",
            "password": "hunter2pass",
        },
    )
    assert resp.status_code == 409


def test_create_user_rejects_pilot_role(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _make_admin(db_session, user)
    resp = client.post(
        "/api/v1/users",
        json={
            "email": "pilot@test.example",
            "full_name": "A Pilot",
            "role": "PILOT",
            "password": "hunter2pass",
        },
    )
    assert resp.status_code == 422


def test_admin_updates_role_and_deactivates(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _make_admin(db_session, user)
    created = client.post(
        "/api/v1/users",
        json={
            "email": "member@test.example",
            "full_name": "Team Member",
            "role": "CREWING_OFFICER",
            "password": "hunter2pass",
        },
    ).json()

    promoted = client.patch(f"/api/v1/users/{created['id']}", json={"role": "ADMIN"})
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "ADMIN"

    deactivated = client.patch(f"/api/v1/users/{created['id']}", json={"is_active": False})
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False


def test_admin_cannot_self_lockout(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    _make_admin(db_session, user)
    me = str(user.id)
    assert client.patch(f"/api/v1/users/{me}", json={"role": "CREWING_OFFICER"}).status_code == 409
    assert client.patch(f"/api/v1/users/{me}", json={"is_active": False}).status_code == 409
    # A harmless self-update (name) still works.
    ok = client.patch(f"/api/v1/users/{me}", json={"full_name": "Renamed Admin"})
    assert ok.status_code == 200
    assert ok.json()["full_name"] == "Renamed Admin"


def test_update_unknown_user_404(auth_client: tuple[TestClient, User], db_session: Session) -> None:
    client, user = auth_client
    _make_admin(db_session, user)
    resp = client.patch(
        "/api/v1/users/00000000-0000-0000-0000-000000000000",
        json={"full_name": "Ghost"},
    )
    assert resp.status_code == 404
