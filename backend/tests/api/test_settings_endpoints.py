"""Operator settings endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_get_and_patch_operator(auth_client: tuple[TestClient, User]) -> None:
    client, user = auth_client
    resp = client.get("/api/v1/settings/operator")
    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == str(user.operator_id)

    patch = client.patch(
        "/api/v1/settings/operator",
        json={"name": "Renamed Operator", "tier": "STANDARD"},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["name"] == "Renamed Operator"
    assert patch.json()["tier"] == "STANDARD"
