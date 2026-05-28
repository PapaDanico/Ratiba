"""LLM usage logging — structured log + optional DB persistence."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from app.models.llm_usage import LlmUsageEvent
from app.services import llm_client


@pytest.fixture
def stub_anthropic(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Replace the lazy ``_client`` constructor with a mock."""
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="hello")]
    fake_response.usage = MagicMock(input_tokens=42, output_tokens=11)
    fake_response.model = "claude-haiku-4-5"

    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_response

    monkeypatch.setattr(llm_client, "_client", lambda: fake_client)
    return fake_client


def test_emits_structured_log_line(
    stub_anthropic: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Monkeypatch the module-level logger directly rather than relying on
    # pytest's caplog / a root handler — global logging config is reconfigured
    # by the FastAPI app's startup in other tests, which makes log-capture
    # order-dependent. Asserting on the logger's call args is hermetic and
    # tests exactly the contract: a structured "llm_usage" line is emitted.
    calls: list[tuple[str, dict[str, Any]]] = []

    def _record(msg: str, *_args: Any, **kwargs: Any) -> None:
        calls.append((msg, kwargs.get("extra", {})))

    monkeypatch.setattr(llm_client.log, "info", _record)

    result = llm_client.conversational_route(system="sys", user_message="hi")
    assert result.input_tokens == 42

    usage = [extra for msg, extra in calls if msg == "llm_usage"]
    assert len(usage) == 1
    payload = usage[0]
    assert payload["call_site"] == "conversational_route"
    assert payload["model"] == "claude-haiku-4-5"
    assert payload["input_tokens"] == 42
    assert payload["output_tokens"] == 11


def test_persists_to_session_when_supplied(stub_anthropic: MagicMock) -> None:
    session = MagicMock()
    added: list[Any] = []
    session.add.side_effect = added.append

    llm_client.conversational_route(
        system="sys",
        user_message="hi",
        session=session,
    )
    assert len(added) == 1
    event = added[0]
    assert isinstance(event, LlmUsageEvent)
    assert event.call_site == "conversational_route"
    assert event.input_tokens == 42
    assert event.output_tokens == 11
    assert event.model == "claude-haiku-4-5"


def test_no_session_means_no_db_write(stub_anthropic: MagicMock) -> None:
    # Bot path: no session, but the call still returns + logs without raising.
    result = llm_client.conversational_route(system="sys", user_message="hi")
    assert result.text == "hello"
