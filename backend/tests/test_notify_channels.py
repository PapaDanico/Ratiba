"""Outbound messaging channels — Telegram, email, SMS (all mocked)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.services.notify import _format_sms, _push_email, _push_sms, _push_telegram


def _notice(
    title: str = "Test",
    body: str = "Body",
    category: str = "OPERATIONAL",
    severity: str = "INFO",
    image_url: str | None = None,
    requires_ack: bool = False,
) -> Any:
    return SimpleNamespace(
        title=title,
        body=body,
        category=SimpleNamespace(value=category),
        severity=SimpleNamespace(value=severity),
        image_url=image_url,
        requires_ack=requires_ack,
    )


# ---------------------------------------------------------------------------
# format_sms
# ---------------------------------------------------------------------------


def test_sms_format_includes_icon_and_title() -> None:
    msg = _format_sms(_notice(title="Ramp ops", body="All crew report by 05:30."))
    assert "Ramp ops" in msg
    assert "05:30" in msg


def test_sms_format_truncated_to_155_chars() -> None:
    long_body = "x" * 200
    msg = _format_sms(_notice(body=long_body))
    assert len(msg) <= 160


# ---------------------------------------------------------------------------
# Telegram push
# ---------------------------------------------------------------------------


def test_telegram_sends_to_all_chat_ids() -> None:
    fake_resp = MagicMock()
    fake_resp.status_code = 200

    with patch("app.services.notify.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.return_value = fake_resp
        sent = _push_telegram([111, 222, 333], "hello", "bot:TOKEN")

    assert sent == 3
    assert instance.post.call_count == 3


def test_telegram_skips_failed_sends() -> None:
    responses = [MagicMock(status_code=200), MagicMock(status_code=429)]

    with patch("app.services.notify.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = responses
        sent = _push_telegram([111, 222], "hello", "bot:TOKEN")

    assert sent == 1


def test_telegram_tolerates_connection_error() -> None:
    with patch("app.services.notify.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.side_effect = Exception("network down")
        sent = _push_telegram([111], "hello", "bot:TOKEN")
    assert sent == 0


# ---------------------------------------------------------------------------
# Email push
# ---------------------------------------------------------------------------


def test_email_skipped_when_smtp_host_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    sent = _push_email(["pilot@example.com"], _notice(), "noreply@ratiba.example")
    get_settings.cache_clear()
    assert sent == 0


def test_email_sends_via_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user")
    monkeypatch.setenv("SMTP_PASSWORD", "pass")
    monkeypatch.setenv("SMTP_FROM", "noreply@ratiba.example")
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    from app.core.config import get_settings

    get_settings.cache_clear()

    mock_server = MagicMock()
    with patch("app.services.notify.smtplib.SMTP", return_value=mock_server):
        sent = _push_email(["alice@crew.ke", "bob@crew.ke"], _notice(), "noreply@ratiba.example")
    get_settings.cache_clear()
    assert sent == 2
    assert mock_server.sendmail.call_count == 2
    mock_server.quit.assert_called_once()


# ---------------------------------------------------------------------------
# Africa's Talking SMS push
# ---------------------------------------------------------------------------


def test_sms_skipped_when_no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AT_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    sent = _push_sms(["+254700000001"], "test")
    get_settings.cache_clear()
    assert sent == 0


def test_sms_sends_to_all_recipients(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AT_API_KEY", "test-key")
    monkeypatch.setenv("AT_USERNAME", "sandbox")
    monkeypatch.setenv("AT_SENDER_ID", "Ratiba")
    from app.core.config import get_settings

    get_settings.cache_clear()

    at_response = {
        "SMSMessageData": {
            "Recipients": [
                {"status": "Success", "number": "+254700000001"},
                {"status": "Success", "number": "+254700000002"},
            ]
        }
    }
    fake_resp = MagicMock()
    fake_resp.status_code = 201
    fake_resp.json.return_value = at_response

    with patch("app.services.notify.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.return_value = fake_resp
        sent = _push_sms(["+254700000001", "+254700000002"], "Ramp ops: report by 05:30")

    get_settings.cache_clear()
    assert sent == 2
    call_kwargs = instance.post.call_args
    assert call_kwargs[0][0] == "https://api.africastalking.com/version1/messaging"


def test_sms_handles_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AT_API_KEY", "test-key")
    monkeypatch.setenv("AT_USERNAME", "sandbox")
    from app.core.config import get_settings

    get_settings.cache_clear()

    fake_resp = MagicMock()
    fake_resp.status_code = 500
    fake_resp.text = "Internal Server Error"

    with patch("app.services.notify.httpx.Client") as MockClient:
        instance = MockClient.return_value.__enter__.return_value
        instance.post.return_value = fake_resp
        sent = _push_sms(["+254700000001"], "test")

    get_settings.cache_clear()
    assert sent == 0
