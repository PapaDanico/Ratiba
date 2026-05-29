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
