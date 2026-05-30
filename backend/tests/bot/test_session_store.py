"""Bot pilot-session store — in-process + Redis-backed."""

from __future__ import annotations

from typing import Any

import pytest
from bot.api_client import (
    PilotSessionStore,
    RedisPilotSessionStore,
    build_session_store,
)


class _FakeRedis:
    """Minimal redis-py stand-in: get/setex/delete/ping over a dict."""

    def __init__(self, *, fail: bool = False) -> None:
        self.store: dict[str, bytes] = {}
        self.ttls: dict[str, int] = {}
        self.fail = fail

    def ping(self) -> bool:
        if self.fail:
            raise ConnectionError("redis down")
        return True

    def get(self, key: str) -> bytes | None:
        if self.fail:
            raise ConnectionError("redis down")
        return self.store.get(key)

    def setex(self, key: str, ttl: int, value: str) -> None:
        if self.fail:
            raise ConnectionError("redis down")
        self.store[key] = value.encode() if isinstance(value, str) else value
        self.ttls[key] = ttl

    def delete(self, key: str) -> None:
        if self.fail:
            raise ConnectionError("redis down")
        self.store.pop(key, None)


def test_redis_store_roundtrip_and_ttl() -> None:
    fake = _FakeRedis()
    store = RedisPilotSessionStore(fake, ttl_seconds=1234, prefix="t:")
    assert store.get(42) is None
    store.set(42, "jwt-token")
    assert store.get(42) == "jwt-token"  # bytes decoded back to str
    assert fake.ttls["t:42"] == 1234  # TTL applied
    store.clear(42)
    assert store.get(42) is None


def test_redis_store_degrades_to_unpaired_on_failure() -> None:
    # A transient Redis failure must not crash a handler — get() returns None
    # (the pilot re-pairs) and set/clear are best-effort no-ops.
    store = RedisPilotSessionStore(_FakeRedis(fail=True))
    store.set(1, "x")  # swallowed
    assert store.get(1) is None
    store.clear(1)  # swallowed


def test_build_session_store_falls_back_without_redis() -> None:
    assert isinstance(build_session_store(""), PilotSessionStore)


def test_build_session_store_falls_back_when_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    import redis

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise ConnectionError("no route to host")

    monkeypatch.setattr(redis, "from_url", _boom)
    assert isinstance(build_session_store("redis://nope:6379/0"), PilotSessionStore)


def test_build_session_store_uses_redis_when_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    import redis

    fake = _FakeRedis()
    monkeypatch.setattr(redis, "from_url", lambda *_a, **_k: fake)
    store = build_session_store("redis://redis:6379/0")
    assert isinstance(store, RedisPilotSessionStore)
    store.set(7, "tok")
    assert store.get(7) == "tok"


def test_build_session_store_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # No explicit url → reads REDIS_URL; empty env → in-process.
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert isinstance(build_session_store(), PilotSessionStore)
