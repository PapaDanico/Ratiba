"""Africa's Talking WhatsApp notify channel."""

from __future__ import annotations

import types

import pytest
from fastapi.testclient import TestClient

from app.models.user import User
from app.services import notify


def _settings(**over: object) -> types.SimpleNamespace:
    base: dict[str, object] = {
        "at_api_key": "",
        "at_username": "",
        "at_whatsapp_number": "",
        "telegram_bot_token": "",
        "smtp_host": "",
        "smtp_from": "",
    }
    base.update(over)
    return types.SimpleNamespace(**base)


class _FakeResp:
    def __init__(self, status: int) -> None:
        self.status_code = status
        self.text = ""


class _FakeClient:
    """Records WhatsApp POSTs and returns 200."""

    calls: list[dict[str, object]] = []

    def __init__(self, *_a: object, **_k: object) -> None:
        pass

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *_a: object) -> bool:
        return False

    def post(self, url: str, *, headers: dict | None = None, json: dict | None = None) -> _FakeResp:
        _FakeClient.calls.append({"url": url, "json": json})
        return _FakeResp(200)


def test_push_whatsapp_noops_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(notify, "get_settings", lambda: _settings())
    assert notify._push_whatsapp(["+254700000001"], "hi") == 0


def test_push_whatsapp_sends_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        notify,
        "get_settings",
        lambda: _settings(at_api_key="k", at_username="u", at_whatsapp_number="+254799"),
    )
    _FakeClient.calls = []
    monkeypatch.setattr(notify.httpx, "Client", _FakeClient)
    sent = notify._push_whatsapp(["+254700000001", "+254700000002"], "roster out")
    assert sent == 2
    assert len(_FakeClient.calls) == 2
    payload = _FakeClient.calls[0]["json"]
    assert payload["waNumber"] == "+254799"
    assert payload["phoneNumber"] == "+254700000001"
    assert payload["body"]["message"] == "roster out"


def test_notify_crew_member_routes_to_whatsapp(
    auth_client: tuple[TestClient, User],
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = auth_client
    crew = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "WA-CAP-1",
            "first_name": "Wanjiru",
            "last_name": "Mwangi",
            "role": "CAPT",
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
            "whatsapp_number": "+254712345678",
        },
    ).json()
    # The new field round-trips through the crew API.
    assert crew["whatsapp_number"] == "+254712345678"

    # Only the WhatsApp channel is configured; spy on the sender.
    seen: list[tuple[list[str], str]] = []
    monkeypatch.setattr(notify, "get_settings", lambda: _settings(at_whatsapp_number="+254799"))
    monkeypatch.setattr(
        notify, "_push_whatsapp", lambda nums, text: seen.append((nums, text)) or len(nums)
    )
    total = notify.notify_crew_member(
        db_session, crew_id=crew["id"], subject="Roster", body="published"
    )
    assert total == 1
    assert seen[0][0] == ["+254712345678"]
