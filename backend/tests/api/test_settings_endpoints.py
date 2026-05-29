"""Operator settings endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_get_and_patch_operator(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    resp = client.get("/api/v1/settings/operator")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == str(user.operator_id)
    # New operators default to East Africa Time.
    assert resp.json()["timezone"] == "Africa/Nairobi"

    patch = client.patch(
        "/api/v1/settings/operator",
        json={"name": "Renamed Operator", "tier": "STANDARD"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["name"] == "Renamed Operator"
    assert patch.json()["tier"] == "STANDARD"


def test_patch_operator_timezone(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    ok = client.patch("/api/v1/settings/operator", json={"timezone": "Africa/Mogadishu"})
    assert ok.status_code == 200, ok.text
    assert ok.json()["timezone"] == "Africa/Mogadishu"

    bad = client.patch("/api/v1/settings/operator", json={"timezone": "Mars/Olympus_Mons"})
    assert bad.status_code == 422


def test_account_get_and_rename(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    me = client.get("/api/v1/settings/account")
    assert me.status_code == 200, me.text
    assert me.json()["email"] == user.email

    renamed = client.patch("/api/v1/settings/account", json={"full_name": "Renamed Me"})
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["full_name"] == "Renamed Me"


def test_change_password_flow(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client

    # Wrong current password is rejected without changing anything.
    bad = client.post(
        "/api/v1/settings/account/password",
        json={"current_password": "wrongpass", "new_password": "brandnewpass1"},
    )
    assert bad.status_code == 400

    # Too-short new password fails validation.
    short = client.post(
        "/api/v1/settings/account/password",
        json={"current_password": "hunter2pass", "new_password": "short"},
    )
    assert short.status_code == 422

    # Correct current password changes it.
    ok = client.post(
        "/api/v1/settings/account/password",
        json={"current_password": "hunter2pass", "new_password": "brandnewpass1"},
    )
    assert ok.status_code == 204

    # The new password now logs in; the old one no longer does.
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "brandnewpass1"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "hunter2pass"},
        ).status_code
        == 401
    )
