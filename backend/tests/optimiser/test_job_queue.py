"""Job queue — InProcessJobQueue contract."""

from __future__ import annotations

from typing import Any

from app.core.job_queue import InProcessJobQueue


# A trivial function the queue can resolve and run.
def _echo(payload: dict[str, Any]) -> dict[str, Any]:
    return {"echo": payload}


def _boom(_payload: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("kaboom")


def test_in_process_queue_runs_synchronously_and_returns_finished() -> None:
    q = InProcessJobQueue()
    job = q.enqueue(
        "tests.optimiser.test_job_queue._echo",
        {"hello": "world"},
    )
    assert job.status == "FINISHED"
    assert job.result == {"echo": {"hello": "world"}}
    assert q.fetch(job.id) is job


def test_in_process_queue_captures_errors_as_failed() -> None:
    q = InProcessJobQueue()
    job = q.enqueue("tests.optimiser.test_job_queue._boom", {})
    assert job.status == "FAILED"
    assert job.error is not None and "kaboom" in job.error


def test_fetch_unknown_id_returns_none() -> None:
    q = InProcessJobQueue()
    assert q.fetch("does-not-exist") is None
