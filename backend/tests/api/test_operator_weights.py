"""Operator-level default soft-constraint weights."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def test_default_weights_are_empty_initially(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    resp = client.get("/api/v1/settings/operator")
    assert resp.status_code == 200
    assert resp.json()["default_soft_weights"] == {}


def test_patch_weights_persists(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.patch(
        "/api/v1/settings/operator",
        json={
            "default_soft_weights": {
                "balance_block_hours": 12.0,
                "faith_violation": 30.0,
            }
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["default_soft_weights"]["balance_block_hours"] == 12.0

    fetched = client.get("/api/v1/settings/operator").json()
    assert fetched["default_soft_weights"]["faith_violation"] == 30.0
