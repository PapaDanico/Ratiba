"""API tests for /api/v1/roster/* — Phase 2."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.job_queue import InProcessJobQueue, get_job_queue
from app.main import create_app


@pytest.fixture
def queue_instance() -> InProcessJobQueue:
    return InProcessJobQueue()


@pytest.fixture
def roster_client(queue_instance: InProcessJobQueue) -> Iterator[TestClient]:
    """Client that injects an in-process queue via FastAPI dependency_overrides.

    Using ``dependency_overrides`` (rather than the global ``set_job_queue``)
    keeps the test queue isolated even when the lifespan would otherwise
    switch to the Redis-backed implementation (e.g. on CI where Redis is up).
    """
    app = create_app()
    app.dependency_overrides[get_job_queue] = lambda: queue_instance
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _small_payload() -> dict[str, Any]:
    horizon_from = date(2026, 6, 15)
    horizon_to = horizon_from + timedelta(days=1)
    return {
        "horizon_from": horizon_from.isoformat(),
        "horizon_to": horizon_to.isoformat(),
        "crew": [
            {
                "crew_id": "CAP-1",
                "role": "CAPT",
                "type_ratings": ["DH8D"],
                "current": True,
            },
            {
                "crew_id": "FO-1",
                "role": "FO",
                "type_ratings": ["DH8D"],
                "current": True,
            },
        ],
        "sectors": [
            {
                "sector_id": "S1",
                "date_local": horizon_from.isoformat(),
                "std": f"{horizon_from.isoformat()}T03:00:00+00:00",  # 06:00 local Nairobi
                "sta": f"{horizon_from.isoformat()}T05:00:00+00:00",
                "aircraft_reg": "5Y-AAA",
                "aircraft_type": "DH8D",
                "block_hours": str(Decimal("2.0")),
            },
        ],
        "timeout_s": 10.0,
    }


def test_generate_returns_job_id_and_finished_inline(
    roster_client: TestClient,
    queue_instance: InProcessJobQueue,
) -> None:
    response = roster_client.post("/api/v1/roster/generate", json=_small_payload())
    assert response.status_code == 202, response.text
    body = response.json()
    assert "job_id" in body
    # InProcessJobQueue runs synchronously, so the job is already FINISHED.
    record = queue_instance.fetch(body["job_id"])
    assert record is not None
    assert record.status == "FINISHED"


def test_get_job_returns_status_and_result(roster_client: TestClient) -> None:
    gen = roster_client.post("/api/v1/roster/generate", json=_small_payload())
    job_id = gen.json()["job_id"]

    response = roster_client.get(f"/api/v1/roster/jobs/{job_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "FINISHED"
    assert body["result"] is not None
    assert body["result"]["status"] in ("OPTIMAL", "FEASIBLE")
    assert len(body["result"]["assignments"]) == 1


def test_get_unknown_job_returns_404(roster_client: TestClient) -> None:
    response = roster_client.get("/api/v1/roster/jobs/does-not-exist")
    assert response.status_code == 404


def test_explain_returns_bindings(roster_client: TestClient) -> None:
    payload = _small_payload()
    duty_day_key = f"5Y-AAA|{payload['horizon_from']}"
    response = roster_client.post(
        "/api/v1/roster/explain",
        json={"duty_day_key": duty_day_key, "input": payload},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["duty_day_key"] == duty_day_key
    assert len(body["bindings"]) >= 3
    rule_ids = [b["rule_id"] for b in body["bindings"]]
    assert "OPT-COVERAGE" in rule_ids
    assert "OPT-FTL" in rule_ids


def test_generate_rejects_empty_crew(roster_client: TestClient) -> None:
    payload = _small_payload()
    payload["crew"] = []
    response = roster_client.post("/api/v1/roster/generate", json=payload)
    assert response.status_code == 422
