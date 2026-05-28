"""Async HTTP client the bot uses to talk to the Ratiba backend.

One client instance per bot process. Per-chat pilot JWTs are tracked in
``PilotSessionStore`` (in-process for Phase 4 MVP — Redis-backed in Phase 6
if/when we run multiple bot replicas).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, cast

import httpx


@dataclass
class PilotSessionStore:
    """chat_id → pilot JWT, in-process."""

    sessions: dict[int, str] = field(default_factory=dict)

    def get(self, chat_id: int) -> str | None:
        return self.sessions.get(chat_id)

    def set(self, chat_id: int, token: str) -> None:
        self.sessions[chat_id] = token

    def clear(self, chat_id: int) -> None:
        self.sessions.pop(chat_id, None)


class BackendError(RuntimeError):
    def __init__(self, status_code: int, body: Any) -> None:
        detail = body.get("detail") if isinstance(body, dict) else str(body)
        super().__init__(f"backend returned {status_code}: {detail}")
        self.status_code = status_code
        self.body = body


class RatibaApi:
    def __init__(self, base_url: str | None = None, store: PilotSessionStore | None = None) -> None:
        self.base_url = (base_url or os.environ.get("BACKEND_URL") or "http://backend:8000").rstrip(
            "/"
        )
        self.store = store or PilotSessionStore()
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=15.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    # -- pairing -------------------------------------------------------------

    async def pair(self, *, code: str, chat_id: int) -> dict[str, Any]:
        resp = await self._client.post(
            "/api/v1/auth/pilot-pair",
            json={"code": code, "telegram_chat_id": chat_id},
        )
        body = resp.json()
        if resp.status_code != 200:
            raise BackendError(resp.status_code, body)
        self.store.set(chat_id, body["pilot_token"])
        return cast("dict[str, Any]", body)

    # -- pilot-scoped calls --------------------------------------------------

    def _headers(self, chat_id: int) -> dict[str, str]:
        token = self.store.get(chat_id)
        if token is None:
            raise BackendError(
                401,
                {"detail": "not paired — send /start <code> first"},
            )
        return {"Authorization": f"Bearer {token}"}

    async def _get(self, chat_id: int, path: str, **kwargs: Any) -> dict[str, Any]:
        resp = await self._client.get(path, headers=self._headers(chat_id), **kwargs)
        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            if resp.status_code == 401:
                self.store.clear(chat_id)
            raise BackendError(resp.status_code, body)
        return cast("dict[str, Any]", body)

    async def _post(self, chat_id: int, path: str, *, json: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(path, headers=self._headers(chat_id), json=json)
        body = resp.json() if resp.content else {}
        if resp.status_code >= 400:
            if resp.status_code == 401:
                self.store.clear(chat_id)
            raise BackendError(resp.status_code, body)
        return cast("dict[str, Any]", body)

    async def me(self, chat_id: int) -> dict[str, Any]:
        return await self._get(chat_id, "/api/v1/crew/me")

    async def roster(
        self, chat_id: int, *, date_from: str | None = None, date_to: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        return await self._get(chat_id, "/api/v1/crew/me/roster", params=params)

    async def duty_today(self, chat_id: int) -> dict[str, Any]:
        return await self._get(chat_id, "/api/v1/crew/me/duty")

    async def currency(self, chat_id: int) -> dict[str, Any]:
        return await self._get(chat_id, "/api/v1/crew/me/currency")

    async def submit_leave(
        self,
        chat_id: int,
        *,
        type_: str,
        date_from: str,
        date_to: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            chat_id,
            "/api/v1/crew/me/leave",
            json={
                "type": type_,
                "date_from": date_from,
                "date_to": date_to,
                "note": note,
            },
        )

    async def submit_swap(
        self,
        chat_id: int,
        *,
        counterparty_employee_no: str,
        fdp_or_sector_ref: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return await self._post(
            chat_id,
            "/api/v1/crew/me/swap",
            json={
                "counterparty_employee_no": counterparty_employee_no,
                "fdp_or_sector_ref": fdp_or_sector_ref,
                "reason": reason,
            },
        )
