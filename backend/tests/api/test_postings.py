"""Outstation / ACMI postings — duration cap, permit gate, overlap."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Crew, User
from app.models.crew import ContractType, CrewRole
from app.models.document import CrewDocument, DocumentType


def _mk_crew(db: Session, operator_id, employee_no: str, role: CrewRole = CrewRole.CAPT) -> Crew:
    c = Crew(
        operator_id=operator_id,
        employee_no=employee_no,
        first_name="Test",
        last_name=employee_no,
        role=role,
        date_of_hire=date(2020, 1, 1),
        date_of_birth=date(1990, 1, 1),
        base_station="HKJK",
        contract_type=ContractType.FULL_TIME,
        active=True,
        languages=[],
        faith_observance_flags={},
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _posting_body(icao: str, country: str, ptype: str, d0: int, d1: int) -> dict:
    today = date.today()
    return {
        "location_icao": icao,
        "country": country,
        "type": ptype,
        "start_date": (today + timedelta(days=d0)).isoformat(),
        "end_date": (today + timedelta(days=d1)).isoformat(),
    }


def test_create_posting_and_duration_cap(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    ok = client.post("/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 0, 20))
    assert ok.status_code == 201, ok.text
    assert ok.json()["duration_days"] == 21

    too_long = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 0, 40)
    )
    assert too_long.status_code == 422
    assert "rotation limit" in too_long.json()["detail"]

    reversed_dates = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 5, 1)
    )
    assert reversed_dates.status_code == 422


def test_assign_domestic_crew(auth_client: tuple[TestClient, User], db_session: Session) -> None:
    client, user = auth_client
    crew = _mk_crew(db_session, user.operator_id, "CAP-1")
    pid = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 0, 10)
    ).json()["id"]
    resp = client.post(f"/api/v1/postings/{pid}/assign", json={"crew_id": str(crew.id)})
    assert resp.status_code == 200, resp.text
    assert {m["employee_no"] for m in resp.json()["crew"]} == {"CAP-1"}


def test_engineer_cover_flag(auth_client: tuple[TestClient, User], db_session: Session) -> None:
    client, user = auth_client
    pilot = _mk_crew(db_session, user.operator_id, "CAP-9", CrewRole.CAPT)
    eng = _mk_crew(db_session, user.operator_id, "ENG-9", CrewRole.ENGINEER)
    pid = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 0, 10)
    ).json()["id"]

    after_pilot = client.post(f"/api/v1/postings/{pid}/assign", json={"crew_id": str(pilot.id)})
    assert after_pilot.json()["engineer_cover"] is False

    after_eng = client.post(f"/api/v1/postings/{pid}/assign", json={"crew_id": str(eng.id)})
    assert after_eng.json()["engineer_cover"] is True


def test_international_posting_requires_permit(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    crew = _mk_crew(db_session, user.operator_id, "CAP-2")
    pid = client.post(
        "/api/v1/postings", json=_posting_body("HUEN", "Uganda", "ACMI_WET_LEASE", 0, 14)
    ).json()["id"]

    # No work permit → blocked.
    denied = client.post(f"/api/v1/postings/{pid}/assign", json={"crew_id": str(crew.id)})
    assert denied.status_code == 422
    assert "work permit" in denied.json()["detail"]

    # Add a valid work permit → allowed.
    db_session.add(
        CrewDocument(
            operator_id=user.operator_id,
            crew_id=crew.id,
            doc_type=DocumentType.WORK_PERMIT,
            expiry_date=date.today() + timedelta(days=60),
        )
    )
    db_session.commit()
    allowed = client.post(f"/api/v1/postings/{pid}/assign", json={"crew_id": str(crew.id)})
    assert allowed.status_code == 200, allowed.text


def test_overlapping_postings_rejected(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    crew = _mk_crew(db_session, user.operator_id, "CAP-3")
    p1 = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 0, 10)
    ).json()["id"]
    p2 = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 5, 15)
    ).json()["id"]
    assert (
        client.post(f"/api/v1/postings/{p1}/assign", json={"crew_id": str(crew.id)}).status_code
        == 200
    )
    clash = client.post(f"/api/v1/postings/{p2}/assign", json={"crew_id": str(crew.id)})
    assert clash.status_code == 422
    assert "overlapping" in clash.json()["detail"]


def test_rotation_due_flag(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    # Ending in 3 days → rotation due.
    soon = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", -5, 3)
    ).json()
    assert soon["rotation_due"] is True
    assert soon["days_to_end"] == 3
    # Ending in 20 days → not due yet.
    later = client.post(
        "/api/v1/postings", json=_posting_body("HKMO", "Kenya", "DETACHMENT", 0, 20)
    ).json()
    assert later["rotation_due"] is False
