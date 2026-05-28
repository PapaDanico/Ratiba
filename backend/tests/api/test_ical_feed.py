"""Per-crew iCalendar roster feed."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import FlightDutyPeriod, User
from app.models.ftl import FdpType, LegalityState


def _create_crew(client: TestClient, *, employee_no: str = "I1") -> dict:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": employee_no,
            "first_name": "Ilana",
            "last_name": "Cal",
            "role": "CAPT",
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()


def test_calendar_feed_roundtrip(
    auth_client: tuple[TestClient, User],
    db_session: Session,
) -> None:
    client, user = auth_client
    crew = _create_crew(client)
    crew_id = uuid.UUID(crew["id"])

    # A published FDP today so the feed has an event.
    today = date.today()
    report = datetime.combine(today, datetime.min.time(), tzinfo=UTC) + timedelta(hours=7)
    db_session.add(
        FlightDutyPeriod(
            operator_id=user.operator_id,
            crew_id=crew_id,
            date=today,
            report_time=report,
            off_duty_time=report + timedelta(hours=5),
            sectors_count=2,
            flight_hours=3.5,
            duty_hours=5.0,
            type=FdpType.FDP,
            legality_state=LegalityState.LEGAL,
        )
    )
    db_session.commit()

    # Mint the feed URL (authenticated).
    feed = client.post(f"/api/v1/crew/{crew_id}/calendar-feed")
    assert feed.status_code == 200, feed.text
    token = feed.json()["token"]
    path = feed.json()["path"]
    assert path == f"/api/v1/crew/{crew_id}/roster.ics?token={token}"

    # Fetch the feed — the endpoint ignores any auth header; the URL token
    # is the credential.
    ics = client.get(f"/api/v1/crew/{crew_id}/roster.ics", params={"token": token})
    assert ics.status_code == 200, ics.text
    assert ics.headers["content-type"].startswith("text/calendar")
    body = ics.text
    assert "BEGIN:VCALENDAR" in body
    assert "BEGIN:VEVENT" in body
    assert "Flight duty" in body
    assert body.strip().endswith("END:VCALENDAR")


def test_feed_rejects_bad_token(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    crew = _create_crew(client, employee_no="I2")
    resp = client.get(f"/api/v1/crew/{crew['id']}/roster.ics", params={"token": "not-a-jwt"})
    assert resp.status_code == 401


def test_feed_rejects_token_for_other_crew(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    a = _create_crew(client, employee_no="I3")
    b = _create_crew(client, employee_no="I4")
    token = client.post(f"/api/v1/crew/{a['id']}/calendar-feed").json()["token"]
    # Use crew A's token on crew B's feed → rejected.
    resp = client.get(f"/api/v1/crew/{b['id']}/roster.ics", params={"token": token})
    assert resp.status_code == 401
