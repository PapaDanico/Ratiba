"""Scheduled recurrency-digest runner (scripts/run_digests.py)."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Crew, CrewCurrency, User
from app.models.crew import ContractType, CrewRole
from app.models.training import CurrencyType


def test_run_digests_covers_every_operator(
    auth_client: tuple[TestClient, User], db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    # auth_client seeds one operator + user. Give it a lapsing currency so the
    # digest has something to report.
    _client, user = auth_client
    crew = Crew(
        operator_id=user.operator_id,
        employee_no="DG-1",
        first_name="Dig",
        last_name="One",
        role=CrewRole.CAPT,
        date_of_hire=date(2020, 1, 1),
        date_of_birth=date(1985, 1, 1),
        base_station="HKJK",
        contract_type=ContractType.FULL_TIME,
        active=True,
        languages=[],
        faith_observance_flags={},
    )
    db_session.add(crew)
    db_session.commit()
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

    calls: list[str] = []

    def _spy(payload: dict) -> dict:  # type: ignore[type-arg]
        calls.append(payload["operator_id"])
        return {"items": 1, "emailed": 0}

    import scripts.run_digests as rd

    monkeypatch.setattr(rd, "notify_expiry_digest", _spy)
    assert rd.main([]) == 0
    # The seeded operator was included.
    assert str(user.operator_id) in calls
