"""Per-crew monthly roster PDF endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def _create_crew(client: TestClient) -> str:
    resp = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "EMP001",
            "first_name": "Amani",
            "last_name": "Otieno",
            "role": "CAPT",
            "date_of_hire": "2020-01-15",
            "date_of_birth": "1985-06-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["id"])


def test_monthly_pdf_for_crew_with_no_duties(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    resp = client.get(
        f"/api/v1/roster/crew/{crew_id}/monthly-pdf",
        params={"year": 2025, "month": 6},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    # WeasyPrint output always starts with the PDF magic bytes.
    assert resp.content[:5] == b"%PDF-"
    assert "attachment" in resp.headers["content-disposition"]


def test_monthly_pdf_unknown_crew_404(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/roster/crew/00000000-0000-0000-0000-000000000000/monthly-pdf",
        params={"year": 2025, "month": 6},
    )
    assert resp.status_code == 404


def test_monthly_pdf_rejects_bad_month(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew_id = _create_crew(client)
    resp = client.get(
        f"/api/v1/roster/crew/{crew_id}/monthly-pdf",
        params={"year": 2025, "month": 13},
    )
    # FastAPI Query(le=12) validation rejects before the handler runs.
    assert resp.status_code == 422
