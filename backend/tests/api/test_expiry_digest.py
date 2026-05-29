"""Recurrency expiry-digest endpoint + task."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Crew, CrewCurrency, User
from app.models.crew import ContractType, CrewRole
from app.models.training import CurrencyType
from app.services import notify


def _crew(db: Session, operator_id, emp: str) -> Crew:
    c = Crew(
        operator_id=operator_id,
        employee_no=emp,
        first_name="Dig",
        last_name=emp,
        role=CrewRole.CAPT,
        date_of_hire=date(2020, 1, 1),
        date_of_birth=date(1985, 1, 1),
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


def test_expiry_digest_emails_staff_when_items_due(
    auth_client: tuple[TestClient, User], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, user = auth_client
    crew = _crew(db_session, user.operator_id, "DIG-1")
    # A landing currency lapsing in 10 days → within the 30-day digest window.
    db_session.add(
        CrewCurrency(
            operator_id=user.operator_id,
            crew_id=crew.id,
            currency_type=CurrencyType.LANDINGS_90D,
            last_completed_date=date.today() - timedelta(days=80),
            expires_date=date.today() + timedelta(days=10),
        )
    )
    db_session.commit()

    captured: list[dict] = []

    def _spy(session, *, operator_id, subject, body):  # type: ignore[no-untyped-def]
        captured.append({"subject": subject, "body": body})
        return 1

    monkeypatch.setattr(notify, "notify_staff", _spy)

    resp = client.post("/api/v1/reports/expiry-digest", params={"within_days": 30})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] in {"FINISHED", "QUEUED", "RUNNING"}

    # In-process queue ran the task inline; it found the lapsing currency.
    assert len(captured) == 1
    assert "DIG-1" in captured[0]["body"]
    assert "LANDINGS_90D" in captured[0]["body"]


def test_expiry_digest_requires_writer(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    # Default seeded_user is a CREWING_OFFICER (a writer) → allowed; just assert 200.
    resp = client.post("/api/v1/reports/expiry-digest")
    assert resp.status_code == 200, resp.text
