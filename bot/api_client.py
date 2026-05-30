"""Async HTTP client the bot uses to talk to the Ratiba backend.

One client instance per bot process. Per-chat pilot JWTs are tracked in a
:class:`SessionStore`: in-process by default, or Redis-backed (shared across
bot replicas) when ``REDIS_URL`` points at a reachable Redis.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

import httpx

logger = logging.getLogger(__name__)

# Pilot tokens are issued for 30 days; expire cached sessions on the same clock
# so a Redis-backed store doesn't accumulate dead entries.
_PILOT_SESSION_TTL_SECONDS = 30 * 86_400


class SessionStore(Protocol):
    """chat_id → pilot JWT. Implemented in-process and over Redis."""

    def get(self, chat_id: int) -> str | None: ...
    def set(self, chat_id: int, token: str) -> None: ...
    def clear(self, chat_id: int) -> None: ...


@dataclass
class PilotSessionStore:
    """chat_id → pilot JWT, in-process. Fine for a single bot replica."""

    sessions: dict[int, str] = field(default_factory=dict)

    def get(self, chat_id: int) -> str | None:
        return self.sessions.get(chat_id)

    def set(self, chat_id: int, token: str) -> None:
        self.sessions[chat_id] = token

    def clear(self, chat_id: int) -> None:
        self.sessions.pop(chat_id, None)


class RedisPilotSessionStore:
    """chat_id → pilot JWT, in Redis — survives a bot restart and is shared
    across replicas. Resilient: a Redis blip degrades to "not paired" (the
    pilot re-pairs) rather than crashing a handler."""

    def __init__(
        self,
        client: Any,
        *,
        ttl_seconds: int = _PILOT_SESSION_TTL_SECONDS,
        prefix: str = "ratiba:bot:session:",
    ) -> None:
        self._redis = client
        self._ttl = ttl_seconds
        self._prefix = prefix

    def _key(self, chat_id: int) -> str:
        return f"{self._prefix}{chat_id}"

    def get(self, chat_id: int) -> str | None:
        try:
            raw = self._redis.get(self._key(chat_id))
        except Exception as exc:  # pragma: no cover - transient redis failure
            logger.warning("bot session read failed (%r) — treating as unpaired", exc)
            return None
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else str(raw)

    def set(self, chat_id: int, token: str) -> None:
        try:
            self._redis.setex(self._key(chat_id), self._ttl, token)
        except Exception as exc:  # pragma: no cover - transient redis failure
            logger.warning("bot session write failed (%r)", exc)

    def clear(self, chat_id: int) -> None:
        try:
            self._redis.delete(self._key(chat_id))
        except Exception as exc:  # pragma: no cover - transient redis failure
            logger.warning("bot session clear failed (%r)", exc)


def build_session_store(
    redis_url: str | None = None,
    *,
    ttl_seconds: int = _PILOT_SESSION_TTL_SECONDS,
) -> SessionStore:
    """Return a Redis-backed store when ``REDIS_URL`` is set and reachable,
    otherwise the in-process one. Mirrors the backend's queue selection: the
    choice is made once, at startup, with a graceful fallback."""
    url = redis_url if redis_url is not None else os.environ.get("REDIS_URL", "").strip()
    if url:
        try:
            import redis

            client = redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
            client.ping()
            logger.info("bot session store: Redis-backed")
            return RedisPilotSessionStore(client, ttl_seconds=ttl_seconds)
        except Exception as exc:
            logger.warning("Redis unavailable (%r) — bot sessions are in-process only", exc)
    return PilotSessionStore()


class BackendError(RuntimeError):
    def __init__(self, status_code: int, body: Any) -> None:
        detail = body.get("detail") if isinstance(body, dict) else str(body)
        super().__init__(f"backend returned {status_code}: {detail}")
        self.status_code = status_code
        self.body = body


class RatibaApi:
    def __init__(self, base_url: str | None = None, store: SessionStore | None = None) -> None:
        self.base_url = (base_url or os.environ.get("BACKEND_URL") or "http://backend:8000").rstrip(
            "/"
        )
        self.store = store if store is not None else build_session_store()
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

    async def notices(self, chat_id: int) -> list[dict[str, Any]]:
        resp = await self._client.get("/api/v1/crew/me/notices", headers=self._headers(chat_id))
        body = resp.json() if resp.content else []
        if resp.status_code >= 400:
            if resp.status_code == 401:
                self.store.clear(chat_id)
            raise BackendError(resp.status_code, body)
        return cast("list[dict[str, Any]]", body)

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
