"""Pure bot handler tests — no Telegram, no Anthropic, no network."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from bot import handlers
from bot.api_client import BackendError, PilotSessionStore


class FakeRatibaApi:
    """In-memory stand-in for :class:`bot.api_client.RatibaApi`."""

    def __init__(self, *, pair_response: dict[str, Any] | None = None) -> None:
        self.store = PilotSessionStore()
        self.pair_calls: list[dict[str, Any]] = []
        self.leave_calls: list[dict[str, Any]] = []
        self.swap_calls: list[dict[str, Any]] = []
        self._pair_response = pair_response
        self.roster_payload: dict[str, Any] = {
            "date_from": "2026-06-15",
            "date_to": "2026-06-28",
            "duty_days": [],
        }
        self.duty_payload: dict[str, Any] = {"has_duty": False}
        self.currency_payload: dict[str, Any] = {"currencies": []}
        self.notices_payload: list[dict[str, Any]] = []
        self.fail_with_401: bool = False

    async def pair(self, *, code: str, chat_id: int) -> dict[str, Any]:
        self.pair_calls.append({"code": code, "chat_id": chat_id})
        if self._pair_response is None:
            raise BackendError(400, {"detail": "unknown pairing code"})
        self.store.set(chat_id, "fake-token")
        return self._pair_response

    def _check_paired(self, chat_id: int) -> None:
        if self.fail_with_401 or self.store.get(chat_id) is None:
            raise BackendError(401, {"detail": "not paired"})

    async def roster(
        self, chat_id: int, *, date_from: str | None = None, date_to: str | None = None
    ) -> dict[str, Any]:
        self._check_paired(chat_id)
        return self.roster_payload

    async def duty_today(self, chat_id: int) -> dict[str, Any]:
        self._check_paired(chat_id)
        return self.duty_payload

    async def currency(self, chat_id: int) -> dict[str, Any]:
        self._check_paired(chat_id)
        return self.currency_payload

    async def notices(self, chat_id: int) -> list[dict[str, Any]]:
        self._check_paired(chat_id)
        return self.notices_payload

    async def submit_leave(
        self,
        chat_id: int,
        *,
        type_: str,
        date_from: str,
        date_to: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        self._check_paired(chat_id)
        call = {
            "chat_id": chat_id,
            "type": type_,
            "date_from": date_from,
            "date_to": date_to,
            "note": note,
        }
        self.leave_calls.append(call)
        return {
            "type": type_,
            "date_from": date_from,
            "date_to": date_to,
            "status": "PENDING",
        }

    async def submit_swap(
        self,
        chat_id: int,
        *,
        counterparty_employee_no: str,
        fdp_or_sector_ref: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        self._check_paired(chat_id)
        call = {
            "chat_id": chat_id,
            "counterparty": counterparty_employee_no,
            "ref": fdp_or_sector_ref,
            "reason": reason,
        }
        self.swap_calls.append(call)
        return {"fdp_or_sector_ref": fdp_or_sector_ref, "status": "PENDING"}


@pytest.fixture
def api() -> FakeRatibaApi:
    return FakeRatibaApi(
        pair_response={
            "pilot_token": "x",
            "crew_id": "00000000-0000-0000-0000-000000000001",
            "employee_no": "P001",
            "role": "CAPT",
            "operator_id": "00000000-0000-0000-0000-000000000002",
        },
    )


@pytest.fixture
def disable_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force the NLP router to keyword-fallback (no LLM)."""
    from bot import nlp_router

    from app.services import llm_client

    def _raise(**_kwargs: Any) -> Any:
        raise llm_client.LlmClientNotConfigured("test")

    monkeypatch.setattr(nlp_router.llm_client, "conversational_route", _raise)
    yield


# --- /start -----------------------------------------------------------------


async def test_start_without_code_returns_instructions(api: FakeRatibaApi) -> None:
    reply = await handlers.handle_start(args=[], chat_id=1, api=api)  # type: ignore[arg-type]
    assert "pairing code" in reply.lower()


async def test_start_with_code_pairs(api: FakeRatibaApi) -> None:
    reply = await handlers.handle_start(args=["abc12345"], chat_id=1, api=api)  # type: ignore[arg-type]
    assert "Paired" in reply
    assert api.pair_calls == [{"code": "ABC12345", "chat_id": 1}]


async def test_start_with_unknown_code_surfaces_error() -> None:
    api = FakeRatibaApi(pair_response=None)
    reply = await handlers.handle_start(args=["NOPE"], chat_id=1, api=api)  # type: ignore[arg-type]
    assert "Could not pair" in reply
    assert "unknown" in reply.lower()


# --- pilot-scoped commands --------------------------------------------------


async def test_duty_without_pairing_says_to_pair(api: FakeRatibaApi) -> None:
    api.store.clear(1)
    api.fail_with_401 = True
    # When using handle_free_text we bubble up via BackendError; direct
    # handler call also raises BackendError because we didn't pair.
    with pytest.raises(BackendError):
        await handlers.handle_duty(chat_id=1, api=api)  # type: ignore[arg-type]


async def test_duty_today_no_duty(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    api.duty_payload = {"has_duty": False}
    reply = await handlers.handle_duty(chat_id=1, api=api)  # type: ignore[arg-type]
    assert "No duty" in reply


async def test_duty_today_with_assignment(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    api.duty_payload = {
        "has_duty": True,
        "duty_day": {
            "date_local": "2026-06-15",
            "aircraft_reg": "5Y-AAA",
            "aircraft_type": "DH8D",
            "sector_ids": ["RB101", "RB102"],
            "role_on_duty": "CAPT",
            "report_time": "2026-06-15T05:00:00+00:00",
            "off_duty_time": "2026-06-15T11:30:00+00:00",
            "flight_hours": "4.0",
            "duty_hours": "6.5",
            "legality_state": "LEGAL",
        },
    }
    reply = await handlers.handle_duty(chat_id=1, api=api)  # type: ignore[arg-type]
    assert "5Y-AAA" in reply
    assert "RB101" in reply
    assert "LEGAL" in reply


async def test_roster_empty(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    reply = await handlers.handle_roster(chat_id=1, api=api)  # type: ignore[arg-type]
    assert "No duty days" in reply


async def test_notices_empty(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    api.notices_payload = []
    reply = await handlers.handle_notices(chat_id=1, api=api)  # type: ignore[arg-type]
    assert "No notices" in reply


async def test_notices_render(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    api.notices_payload = [
        {
            "category": "SAFETY",
            "severity": "CRITICAL",
            "title": "Bird activity",
            "body": "Vigilance on approach.",
            "pinned": True,
            "requires_ack": True,
            "acknowledged": False,
            "image_url": None,
        }
    ]
    reply = await handlers.handle_notices(chat_id=1, api=api)  # type: ignore[arg-type]
    assert "Bird activity" in reply
    assert "Safety" in reply
    assert "acknowledge" in reply.lower()


async def test_free_text_routes_to_notices(api: FakeRatibaApi, disable_llm: None) -> None:
    api.store.set(7, "x")
    api.notices_payload = []
    reply = await handlers.handle_free_text(
        text="any notices today?",
        chat_id=7,
        api=api,  # type: ignore[arg-type]
    )
    assert "No notices" in reply


async def test_currency_renders_traffic_light(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    api.currency_payload = {
        "currencies": [
            {
                "currency_type": "OPC",
                "expires_date": "2026-12-01",
                "days_remaining": 180,
                "state": "GREEN",
            },
            {
                "currency_type": "LPC",
                "expires_date": "2026-06-20",
                "days_remaining": 5,
                "state": "AMBER",
            },
        ]
    }
    reply = await handlers.handle_currency(chat_id=1, api=api)  # type: ignore[arg-type]
    assert "OPC" in reply
    assert "LPC" in reply
    assert "🟢" in reply  # GREEN icon
    assert "🟡" in reply  # AMBER icon


# --- /leave + /swap --------------------------------------------------------


async def test_leave_submit_happy_path(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    reply = await handlers.handle_leave_submit(
        args=["ANNUAL", "2026-07-01", "2026-07-07", "Family", "event"],
        chat_id=1,
        api=api,  # type: ignore[arg-type]
    )
    assert "Leave request submitted" in reply
    assert api.leave_calls == [
        {
            "chat_id": 1,
            "type": "ANNUAL",
            "date_from": "2026-07-01",
            "date_to": "2026-07-07",
            "note": "Family event",
        }
    ]


async def test_leave_submit_help_when_no_args(api: FakeRatibaApi) -> None:
    reply = await handlers.handle_leave_submit(args=[], chat_id=1, api=api)  # type: ignore[arg-type]
    assert "/leave" in reply
    assert api.leave_calls == []


async def test_swap_submit_happy_path(api: FakeRatibaApi) -> None:
    api.store.set(1, "x")
    reply = await handlers.handle_swap_submit(
        args=["P012", "RB101-2026-07-15", "Doctor", "appt"],
        chat_id=1,
        api=api,  # type: ignore[arg-type]
    )
    assert "Swap request submitted" in reply
    assert api.swap_calls == [
        {
            "chat_id": 1,
            "counterparty": "P012",
            "ref": "RB101-2026-07-15",
            "reason": "Doctor appt",
        }
    ]


# --- free-text + intent routing --------------------------------------------


async def test_free_text_routes_to_duty(api: FakeRatibaApi, disable_llm: None) -> None:
    api.store.set(99, "x")
    api.duty_payload = {"has_duty": False}
    reply = await handlers.handle_free_text(
        text="do i fly today?",
        chat_id=99,
        api=api,  # type: ignore[arg-type]
    )
    assert "No duty" in reply


async def test_free_text_routes_to_currency(api: FakeRatibaApi, disable_llm: None) -> None:
    api.store.set(99, "x")
    reply = await handlers.handle_free_text(
        text="when does my OPC expire?",
        chat_id=99,
        api=api,  # type: ignore[arg-type]
    )
    assert "No currencies" in reply or "OPC" in reply


async def test_free_text_unknown_falls_back_to_help(api: FakeRatibaApi, disable_llm: None) -> None:
    reply = await handlers.handle_free_text(
        text="purple monkey dishwasher",
        chat_id=1,
        api=api,  # type: ignore[arg-type]
    )
    assert "Ratiba" in reply  # help text mentions the product name


async def test_free_text_401_prompts_pairing(api: FakeRatibaApi, disable_llm: None) -> None:
    api.fail_with_401 = True
    reply = await handlers.handle_free_text(
        text="roster please",
        chat_id=1,
        api=api,  # type: ignore[arg-type]
    )
    assert "pair" in reply.lower()
