"""Phase 7 — OM-A constraint parser + review endpoints (LLM mocked)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from app.services import llm_client

_FAKE_JSON = (
    '{"rules": ['
    '{"rule_key": "rest_home_floor_h", "value": 14.0,'
    ' "source_excerpt": "Rest at home base: 14h.", "confidence": 0.95},'
    '{"rule_key": "cumul_duty_7d_h", "value": 55.0,'
    ' "source_excerpt": "7-day duty cap 55h.", "confidence": 0.9}'
    "]}"
)


@pytest.fixture
def stub_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text=_FAKE_JSON)]
    fake_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    fake_response.model = "claude-sonnet-4-5"
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response
    monkeypatch.setattr(llm_client, "_client", lambda: fake_client)


def _parse(client: TestClient) -> dict:
    resp = client.post(
        "/api/v1/constraints/parse",
        json={
            "om_a_revision": "Rev 7",
            "om_a_text": "Operator FTL chapter prose...",
            "source_filename": "om-a-ftl.pdf",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_parse_creates_reviewable_set(auth_client: tuple[TestClient, User], stub_llm: None) -> None:
    client, _ = auth_client
    body = _parse(client)
    assert body["status"] == "UNDER_REVIEW"
    assert body["model"] == "claude-sonnet-4-5"
    assert body["rule_count"] == len(body["rules"])

    by_key = {r["rule_key"]: r for r in body["rules"]}
    rest = by_key["rest_home_floor_h"]
    assert rest["proposed_value"] == 14.0
    assert rest["differs_from_baseline"] is True
    assert by_key["at_limit_margin_h"]["proposed_value"] is None
    assert by_key["at_limit_margin_h"]["differs_from_baseline"] is False


def test_list_and_get_set(auth_client: tuple[TestClient, User], stub_llm: None) -> None:
    client, _ = auth_client
    set_id = _parse(client)["id"]

    listed = client.get("/api/v1/constraints").json()
    assert any(s["id"] == set_id for s in listed)

    detail = client.get(f"/api/v1/constraints/{set_id}").json()
    assert detail["id"] == set_id
    assert len(detail["rules"]) == detail["rule_count"]


def test_review_accept_edit_then_finalize(
    auth_client: tuple[TestClient, User], stub_llm: None
) -> None:
    client, _ = auth_client
    detail = _parse(client)
    set_id = detail["id"]
    by_key = {r["rule_key"]: r for r in detail["rules"]}

    # Acceptance is blocked while the parser's proposals are unreviewed.
    blocked = client.post(f"/api/v1/constraints/{set_id}/accept")
    assert blocked.status_code == 409

    # Accept the proposed home-rest floor as-is.
    rest_id = by_key["rest_home_floor_h"]["id"]
    r = client.patch(
        f"/api/v1/constraints/{set_id}/rules/{rest_id}",
        json={"review_status": "ACCEPTED"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["final_value"] == 14.0

    # Edit the 7-day duty cap to a hand-tuned value.
    duty_id = by_key["cumul_duty_7d_h"]["id"]
    r = client.patch(
        f"/api/v1/constraints/{set_id}/rules/{duty_id}",
        json={"review_status": "EDITED", "final_value": 52.0},
    )
    assert r.status_code == 200, r.text
    assert r.json()["final_value"] == 52.0

    # Both proposals handled (unmentioned rules carry no proposal) → accept.
    accepted = client.post(f"/api/v1/constraints/{set_id}/accept")
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "ACCEPTED"
    assert accepted.json()["accepted_at"] is not None

    # A finalised set rejects further edits.
    locked = client.patch(
        f"/api/v1/constraints/{set_id}/rules/{rest_id}",
        json={"review_status": "REJECTED"},
    )
    assert locked.status_code == 409


def test_edit_requires_final_value(auth_client: tuple[TestClient, User], stub_llm: None) -> None:
    client, _ = auth_client
    detail = _parse(client)
    set_id = detail["id"]
    rule_id = detail["rules"][0]["id"]
    r = client.patch(
        f"/api/v1/constraints/{set_id}/rules/{rule_id}",
        json={"review_status": "EDITED"},
    )
    assert r.status_code == 422


def test_comment_trail(auth_client: tuple[TestClient, User], stub_llm: None) -> None:
    client, _ = auth_client
    detail = _parse(client)
    set_id = detail["id"]
    rule_id = detail["rules"][0]["id"]

    c = client.post(
        f"/api/v1/constraints/{set_id}/rules/{rule_id}/comments",
        json={"body": "Confirmed against OM-A Rev 7 §2.3."},
    )
    assert c.status_code == 201, c.text

    fetched = client.get(f"/api/v1/constraints/{set_id}/rules/{rule_id}").json()
    assert len(fetched["comments"]) == 1
    assert fetched["comments"][0]["body"].startswith("Confirmed")


def test_set_scoped_to_operator(auth_client: tuple[TestClient, User], stub_llm: None) -> None:
    client, _ = auth_client
    missing = "00000000-0000-0000-0000-000000000000"
    assert client.get(f"/api/v1/constraints/{missing}").status_code == 404
