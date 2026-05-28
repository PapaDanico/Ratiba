"""Rate-limit primitive — pure unit test, no FastAPI / no DB."""

from __future__ import annotations

import time

from app.core.rate_limit import PAIRING_LIMITER, RateLimiter


def test_within_budget_passes() -> None:
    rl = RateLimiter(max_events=3, window_s=60.0)
    assert rl.hit("k") is True
    assert rl.hit("k") is True
    assert rl.hit("k") is True


def test_over_budget_is_throttled() -> None:
    rl = RateLimiter(max_events=2, window_s=60.0)
    assert rl.hit("k") is True
    assert rl.hit("k") is True
    assert rl.hit("k") is False
    assert rl.hit("k") is False


def test_keys_are_independent() -> None:
    rl = RateLimiter(max_events=1, window_s=60.0)
    assert rl.hit("a") is True
    assert rl.hit("a") is False
    # Different key has its own budget.
    assert rl.hit("b") is True


def test_window_resets_via_time(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """After the window passes the budget refills."""
    rl = RateLimiter(max_events=1, window_s=0.1)
    assert rl.hit("k") is True
    assert rl.hit("k") is False
    # Use a real sleep — the window is only 100 ms.
    time.sleep(0.15)
    assert rl.hit("k") is True


def test_reset_clears_key() -> None:
    rl = RateLimiter(max_events=1, window_s=60.0)
    rl.hit("k")
    assert rl.hit("k") is False
    rl.reset("k")
    assert rl.hit("k") is True


def test_global_pairing_limiter_is_a_RateLimiter() -> None:
    assert isinstance(PAIRING_LIMITER, RateLimiter)
    PAIRING_LIMITER.reset()
    assert PAIRING_LIMITER.hit("x") is True
