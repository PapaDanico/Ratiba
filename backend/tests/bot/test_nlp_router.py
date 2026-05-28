"""NLP router — keyword fallback + LLM-response parsing."""

from __future__ import annotations

from typing import Any

import pytest
from bot import nlp_router

from app.services import llm_client


@pytest.fixture
def force_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(**_kwargs: Any) -> Any:
        raise llm_client.LlmClientNotConfigured("test")

    monkeypatch.setattr(nlp_router.llm_client, "conversational_route", _raise)


def _stub_llm(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    def _fake(**_kwargs: Any) -> llm_client.LlmResponse:
        return llm_client.LlmResponse(
            text=text, input_tokens=10, output_tokens=5, model="claude-haiku-4-5"
        )

    monkeypatch.setattr(nlp_router.llm_client, "conversational_route", _fake)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("show me my roster please", "roster"),
        ("do I fly today?", "duty_today"),
        ("when does my OPC expire", "currency"),
        ("can you swap me out of friday", "swap_help"),
        ("I need annual leave next week", "leave_help"),
        ("hi there", "help"),
    ],
)
def test_keyword_fallback(force_keyword: None, text: str, expected: str) -> None:
    routed = nlp_router.route(text)
    assert routed.intent == expected


def test_llm_valid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_llm(monkeypatch, '{"intent": "duty_today", "confidence": 0.9}')
    routed = nlp_router.route("anything")
    assert routed.intent == "duty_today"
    assert routed.confidence == pytest.approx(0.9)


def test_llm_invalid_json_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_llm(monkeypatch, "this is not json at all")
    routed = nlp_router.route("show me my roster")
    assert routed.intent == "roster"  # keyword fallback


def test_llm_unknown_intent_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_llm(monkeypatch, '{"intent": "blast off", "confidence": 1.0}')
    routed = nlp_router.route("show me my roster")
    assert routed.intent == "roster"


def test_llm_strips_code_fence(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_llm(monkeypatch, '```json\n{"intent": "currency", "confidence": 0.8}\n```')
    routed = nlp_router.route("anything")
    assert routed.intent == "currency"


def test_empty_text_yields_help(force_keyword: None) -> None:
    routed = nlp_router.route("")
    assert routed.intent == "help"


def test_llm_outage_keyword_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(**_kwargs: Any) -> Any:
        raise RuntimeError("anthropic exploded")

    monkeypatch.setattr(nlp_router.llm_client, "conversational_route", _raise)
    routed = nlp_router.route("roster please")
    assert routed.intent == "roster"
