"""Crew taxonomy — cabin crew + engineers alongside flight deck.

`role` is the single source of truth; `crew_category` is derived. Cabin and
engineering crew can be onboarded and listed/filtered, while the pilot-pairing
optimiser only ever sees flight-deck crew.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models import User
from app.models.crew import CrewCategory, CrewRole, category_for_role


def _crew_body(employee_no: str, role: str) -> dict:
    return {
        "employee_no": employee_no,
        "first_name": "Test",
        "last_name": employee_no,
        "role": role,
        "date_of_hire": "2020-01-01",
        "date_of_birth": "1990-01-01",
        "base_station": "HKJK",
        "contract_type": "FULL_TIME",
    }


def test_category_for_role_mapping() -> None:
    assert category_for_role(CrewRole.CAPT) is CrewCategory.FLIGHT_DECK
    assert category_for_role(CrewRole.FO) is CrewCategory.FLIGHT_DECK
    assert category_for_role(CrewRole.SO) is CrewCategory.FLIGHT_DECK
    assert category_for_role(CrewRole.PURSER) is CrewCategory.CABIN
    assert category_for_role(CrewRole.CABIN_CREW) is CrewCategory.CABIN
    assert category_for_role(CrewRole.ENGINEER) is CrewCategory.ENGINEERING


def test_create_and_filter_cabin_and_engineer_crew(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    cases = [
        ("CAP-1", "CAPT", "FLIGHT_DECK"),
        ("CC-1", "CABIN_CREW", "CABIN"),
        ("PUR-1", "PURSER", "CABIN"),
        ("ENG-1", "ENGINEER", "ENGINEERING"),
    ]
    for emp, role, expected_cat in cases:
        resp = client.post("/api/v1/crew", json=_crew_body(emp, role))
        assert resp.status_code == 201, resp.text
        assert resp.json()["crew_category"] == expected_cat

    cabin = client.get("/api/v1/crew?category=CABIN").json()
    assert {c["employee_no"] for c in cabin} == {"CC-1", "PUR-1"}

    eng = client.get("/api/v1/crew?category=ENGINEERING").json()
    assert {c["employee_no"] for c in eng} == {"ENG-1"}

    flight = client.get("/api/v1/crew?category=FLIGHT_DECK").json()
    assert {c["employee_no"] for c in flight} == {"CAP-1"}

    # No filter → everyone.
    everyone = client.get("/api/v1/crew").json()
    assert len(everyone) == 4


def test_unknown_category_rejected(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    assert client.get("/api/v1/crew?category=NONSENSE").status_code == 422
