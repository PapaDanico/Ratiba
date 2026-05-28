"""Crew document management + recurrency integration."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.models.user import User


def _create_crew(client: TestClient, *, employee_no: str = "D1") -> dict:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": employee_no,
            "first_name": "Doc",
            "last_name": "Owino",
            "role": "FO",
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1990-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()


def test_add_list_delete_document(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client)
    today = date.today()
    created = client.post(
        f"/api/v1/documents/crew/{crew['id']}",
        json={
            "doc_type": "MEDICAL",
            "document_number": "MED-123",
            "issuing_authority": "KCAA",
            "issue_date": today.isoformat(),
            "expiry_date": (today + timedelta(days=200)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["doc_type"] == "MEDICAL"
    assert body["crew_name"] == "Doc Owino"
    assert body["state"] == "GREEN"

    listed = client.get("/api/v1/documents").json()
    assert any(d["document_number"] == "MED-123" for d in listed)

    resp = client.delete(f"/api/v1/documents/{body['id']}")
    assert resp.status_code == 204
    assert client.get("/api/v1/documents").json() == []


def test_document_without_expiry_is_na(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client, employee_no="D2")
    created = client.post(
        f"/api/v1/documents/crew/{crew['id']}",
        json={"doc_type": "PASSPORT", "document_number": "P-999"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["state"] == "NA"
    assert body["days_remaining"] is None


def test_expiry_before_issue_rejected(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client, employee_no="D3")
    today = date.today()
    resp = client.post(
        f"/api/v1/documents/crew/{crew['id']}",
        json={
            "doc_type": "VISA",
            "issue_date": today.isoformat(),
            "expiry_date": (today - timedelta(days=5)).isoformat(),
        },
    )
    assert resp.status_code == 422


def test_expiring_document_shows_in_recurrency(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client, employee_no="D4")
    today = date.today()
    client.post(
        f"/api/v1/documents/crew/{crew['id']}",
        json={
            "doc_type": "MEDICAL",
            "expiry_date": (today + timedelta(days=15)).isoformat(),
        },
    ).raise_for_status()

    items = client.get("/api/v1/training/recurrency", params={"within_days": 90}).json()
    medical = [i for i in items if i["kind"] == "document" and i["label"] == "Medical"]
    assert len(medical) == 1
    assert medical[0]["state"] == "AMBER"
    assert medical[0]["crew_name"] == "Doc Owino"
