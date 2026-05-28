"""Simple in-memory leaky-bucket rate limiter.

Used by ``POST /api/v1/auth/pilot-pair`` to throttle pairing-code spam
(5 attempts per minute per ``telegram_chat_id`` or per source IP when
no chat id is supplied).

Single-process only — fine while the bot runs in one replica. Phase 7
swaps to Redis if we horizontally scale.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Final

_DEFAULT_MAX: Final[int] = 5
_DEFAULT_WINDOW_S: Final[float] = 60.0


class RateLimiter:
    def __init__(self, *, max_events: int = _DEFAULT_MAX, window_s: float = _DEFAULT_WINDOW_S):
        self.max_events = max_events
        self.window_s = window_s
        self._lock = Lock()
        self._events: dict[str, deque[float]] = {}

    def hit(self, key: str) -> bool:
        """Returns ``True`` if the call is allowed, ``False`` if rate-limited."""
        now = time.monotonic()
        with self._lock:
            bucket = self._events.setdefault(key, deque())
            while bucket and now - bucket[0] > self.window_s:
                bucket.popleft()
            if len(bucket) >= self.max_events:
                return False
            bucket.append(now)
            return True

    def reset(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._events.clear()
            else:
                self._events.pop(key, None)


# Single global instance — endpoints import and call ``hit`` directly.
PAIRING_LIMITER = RateLimiter(max_events=5, window_s=60.0)
