"""Aircraft fleet registry + aircraft-type reference menu."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User
from app.services import aircraft_types


def test_reference_lists_curated_types(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get("/api/v1/reference/aircraft-types")
    assert resp.status_code == 200
    rows = resp.json()
    icaos = {r["icao"] for r in rows}
    # Spot-check the workhorses of the EAC sub-scale segment.
    assert {"DH8D", "AT76", "C208", "B190", "E145"} <= icaos
    # Every entry carries a dropdown label + category.
    sample = rows[0]
    assert "label" in sample
    assert sample["category"] in {"turboprop", "light", "regional_jet", "narrowbody"}
    assert len(rows) == len(aircraft_types.all_types())


def test_add_aircraft_with_known_type(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/fleet",
        json={"registration": "5y-abc", "aircraft_type": "DH8D"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["registration"] == "5Y-ABC"  # normalised upper
    assert body["aircraft_type_known"] is True


def test_add_aircraft_with_custom_type_flagged(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/fleet",
        json={"registration": "5Y-XYZ", "aircraft_type": "ZZZZ"},
    )
    assert resp.status_code == 201
    assert resp.json()["aircraft_type_known"] is False


def test_duplicate_registration_conflicts(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    client.post(
        "/api/v1/fleet", json={"registration": "5Y-DUP", "aircraft_type": "AT76"}
    ).raise_for_status()
    resp = client.post("/api/v1/fleet", json={"registration": "5Y-DUP", "aircraft_type": "AT76"})
    assert resp.status_code == 409


def test_list_and_patch_fleet(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    created = client.post(
        "/api/v1/fleet", json={"registration": "5Y-PAT", "aircraft_type": "C208"}
    ).json()
    listed = client.get("/api/v1/fleet").json()
    assert any(a["registration"] == "5Y-PAT" for a in listed)

    patched = client.patch(
        f"/api/v1/fleet/{created['id']}",
        json={"active": False, "aircraft_type": "C208B"},
    )
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    assert patched.json()["aircraft_type"] == "C208B"
