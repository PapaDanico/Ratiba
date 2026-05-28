"""Notices (crew comms) — officer authoring + pilot read/ack."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User


def _create_crew_and_pair(client: TestClient, *, emp: str = "N001") -> str:
    client.post(
        "/api/v1/crew",
        json={
            "employee_no": emp,
            "first_name": "Imani",
            "last_name": "Wairimu",
            "role": "FO",
            "date_of_hire": "2022-01-01",
            "date_of_birth": "1993-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).raise_for_status()
    crew_id = client.get("/api/v1/crew").json()[0]["id"]
    code = client.post(f"/api/v1/crew/{crew_id}/pairing-token").json()["code"]
    paired = client.post("/api/v1/auth/pilot-pair", json={"code": code}).json()
    return paired["pilot_token"]


def test_post_and_list_notice(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/notices",
        json={
            "category": "OPERATIONAL",
            "severity": "IMPORTANT",
            "title": "Winter ops",
            "body": "De-icing sign-off required before 07:00 departures.",
            "requires_ack": True,
            "pinned": True,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["title"] == "Winter ops"

    listed = client.get("/api/v1/notices").json()
    assert len(listed) == 1
    assert listed[0]["pinned"] is True
    assert listed[0]["crew_total"] == 0  # no crew yet
    assert listed[0]["ack_count"] == 0


def test_social_notice_with_image(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/notices",
        json={
            "category": "SOCIAL",
            "severity": "INFO",
            "title": "Crew room meme",
            "body": "When the optimiser nails the roster first try 😎",
            "image_url": "https://example.aero/meme.png",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["image_url"] == "https://example.aero/meme.png"
    assert resp.json()["category"] == "SOCIAL"


def test_pilot_sees_and_acknowledges_notice(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    token = _create_crew_and_pair(client)
    notice = client.post(
        "/api/v1/notices",
        json={
            "category": "SAFETY",
            "severity": "CRITICAL",
            "title": "Bird activity HKJK",
            "body": "Heightened vigilance on approach.",
            "requires_ack": True,
        },
    ).json()

    # Switch to the pilot token.
    client.headers["Authorization"] = f"Bearer {token}"
    seen = client.get("/api/v1/crew/me/notices").json()
    assert len(seen) == 1
    assert seen[0]["acknowledged"] is False

    ack = client.post(f"/api/v1/crew/me/notices/{notice['id']}/ack")
    assert ack.status_code == 200
    assert ack.json()["acknowledged"] is True

    seen = client.get("/api/v1/crew/me/notices").json()
    assert seen[0]["acknowledged"] is True


def test_ack_count_reflects_in_officer_list(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    token = _create_crew_and_pair(client)
    notice = client.post(
        "/api/v1/notices",
        json={
            "category": "SAFETY",
            "severity": "CRITICAL",
            "title": "Ack me",
            "body": "Please ack.",
            "requires_ack": True,
        },
    ).json()

    client.headers["Authorization"] = f"Bearer {token}"
    client.post(f"/api/v1/crew/me/notices/{notice['id']}/ack").raise_for_status()

    # Re-login as the officer to read the ack stats.
    del client.headers["Authorization"]
    officer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "officer@test.example", "password": "hunter2pass"},
    ).json()
    client.headers["Authorization"] = f"Bearer {officer_login['access_token']}"
    listed = client.get("/api/v1/notices").json()
    assert listed[0]["ack_count"] == 1
    assert listed[0]["crew_total"] == 1


def test_unpublished_notice_hidden_from_pilot(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    token = _create_crew_and_pair(client)
    client.post(
        "/api/v1/notices",
        json={
            "category": "OPERATIONAL",
            "severity": "INFO",
            "title": "Draft",
            "body": "Not yet published.",
            "published": False,
        },
    ).raise_for_status()

    client.headers["Authorization"] = f"Bearer {token}"
    seen = client.get("/api/v1/crew/me/notices").json()
    assert seen == []
