"""Redis/rq job queue, with a dependency-injectable fake for tests.

Phase 2 only needs enqueue + fetch by id; we hold the abstraction tight so
we can swap to a fuller layer (priorities, retries, scheduling) without
breaking the API surface.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class JobRecord:
    """Lightweight snapshot of a job's lifecycle state."""

    id: str
    status: str  # QUEUED | RUNNING | FINISHED | FAILED
    result: dict[str, Any] | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class JobQueue(Protocol):
    """Minimal interface our endpoints depend on."""

    def enqueue(
        self, func_path: str, payload: dict[str, Any], *, job_id: str | None = None
    ) -> JobRecord: ...
    def fetch(self, job_id: str) -> JobRecord | None: ...


class InProcessJobQueue:
    """Synchronous in-process queue used for tests and local dev.

    ``enqueue`` resolves the ``func_path`` import and runs the function
    immediately, storing the result in memory. Tests can inspect ``self.jobs``
    for assertions.
    """

    def __init__(self) -> None:
        self.jobs: dict[str, JobRecord] = {}

    def _resolve(self, func_path: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
        module_path, func_name = func_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[func_name])
        return getattr(module, func_name)  # type: ignore[no-any-return]

    def enqueue(
        self, func_path: str, payload: dict[str, Any], *, job_id: str | None = None
    ) -> JobRecord:
        jid = job_id or str(uuid.uuid4())
        record = JobRecord(id=jid, status="RUNNING", meta={"func": func_path})
        self.jobs[jid] = record
        try:
            func = self._resolve(func_path)
            record.result = func(payload)
            record.status = "FINISHED"
        except Exception as exc:
            record.error = repr(exc)
            record.status = "FAILED"
        return record

    def fetch(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)


class _RqJobQueue:
    """Redis-backed queue using rq.

    Lazily imports rq so that test environments without it (or without
    Redis) don't import-fail.
    """

    def __init__(self, redis_url: str, queue_name: str = "ratiba") -> None:
        self.redis_url = redis_url
        self.queue_name = queue_name
        self._queue: Any | None = None

    def _q(self) -> Any:
        if self._queue is None:
            import redis
            from rq import Queue

            self._queue = Queue(self.queue_name, connection=redis.from_url(self.redis_url))
        return self._queue

    def enqueue(
        self, func_path: str, payload: dict[str, Any], *, job_id: str | None = None
    ) -> JobRecord:
        job = self._q().enqueue(
            func_path,
            args=(payload,),
            job_id=job_id,
            result_ttl=86400,
            failure_ttl=86400,
        )
        return JobRecord(
            id=job.id,
            status="QUEUED",
            meta={"func": func_path},
        )

    def fetch(self, job_id: str) -> JobRecord | None:
        try:
            from rq.job import Job
        except ImportError:
            return None
        import redis

        try:
            job = Job.fetch(job_id, connection=redis.from_url(self.redis_url))
        except Exception:
            return None
        status_map = {
            "queued": "QUEUED",
            "started": "RUNNING",
            "finished": "FINISHED",
            "failed": "FAILED",
            "deferred": "QUEUED",
            "scheduled": "QUEUED",
        }
        status = status_map.get(job.get_status(refresh=True), "QUEUED")
        result: dict[str, Any] | None = None
        error: str | None = None
        if status == "FINISHED" and job.result is not None:
            result = job.result if isinstance(job.result, dict) else json.loads(job.result)
        if status == "FAILED":
            error = job.exc_info or "job failed"
        return JobRecord(id=job_id, status=status, result=result, error=error)


# -----------------------------------------------------------------------------
# Dependency injection
# -----------------------------------------------------------------------------

_queue: JobQueue | None = None


def get_job_queue() -> JobQueue:
    """FastAPI dependency. Returns a process-wide queue instance."""
    global _queue
    if _queue is None:
        # Default to the in-process queue; production wiring in ``main``
        # can call :func:`set_job_queue` with the Redis-backed implementation.
        _queue = InProcessJobQueue()
    return _queue


def set_job_queue(queue: JobQueue) -> None:
    """Override the global queue. Used by ``main`` and by tests."""
    global _queue
    _queue = queue


def use_redis_queue(redis_url: str) -> JobQueue:
    queue = _RqJobQueue(redis_url=redis_url)
    set_job_queue(queue)
    return queue
