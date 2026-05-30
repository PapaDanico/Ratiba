"""API tests for /api/v1/ftl/validate-fdp and /api/v1/ftl/check."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient


def _base_fdp(*, hour_local: int = 9, duty_h: float = 10.0) -> dict[str, Any]:
    # Africa/Nairobi is UTC+3 year-round.
    report_utc = datetime(2026, 6, 15, hour_local - 3, 0, tzinfo=UTC)
    off_utc = report_utc + timedelta(hours=duty_h)
    return {
        "report_time": report_utc.isoformat(),
        "off_duty_time": off_utc.isoformat(),
        "sectors_count": 2,
        "flight_hours": "8.0",
        "duty_hours": str(duty_h),
        "base_tz": "Africa/Nairobi",
        "fdp_type": "FDP",
        "crew_role": "CAPT",
    }


def test_validate_fdp_returns_aggregated_and_trace(client: TestClient) -> None:
    response = client.post("/api/v1/ftl/validate-fdp", json=_base_fdp())
    assert response.status_code == 200, response.text
    body = response.json()
    assert "aggregated" in body
    assert "rule_trace" in body
    assert body["aggregated"]["legality_state"] == "LEGAL"
    assert len(body["rule_trace"]) >= 3
    rule_ids = [v["rule_id"] for v in body["rule_trace"]]
    assert "KCAR-P8-FDP-MAX-BASIC" in rule_ids


def test_validate_fdp_flags_illegal_duty(client: TestClient) -> None:
    body = _base_fdp(duty_h=20.0)
    response = client.post("/api/v1/ftl/validate-fdp", json=body)
    assert response.status_code == 200
    assert response.json()["aggregated"]["legality_state"] == "ILLEGAL"


def test_validate_fdp_reserve_sleep_opportunity(client: TestClient) -> None:
    # A reserve (standby) duty with too little protected sleep opportunity is
    # flagged by KCAR-P8-RESERVE-SLEEP via the public API.
    body = _base_fdp()
    body["standby_type"] = "SHORT_CALL"
    body["reserve_sleep_opportunity_h"] = "5.0"
    response = client.post("/api/v1/ftl/validate-fdp", json=body)
    assert response.status_code == 200, response.text
    trace = {v["rule_id"]: v["legality_state"] for v in response.json()["rule_trace"]}
    assert trace["KCAR-P8-RESERVE-SLEEP"] == "ILLEGAL"


def test_validate_fdp_rejects_invalid_payload(client: TestClient) -> None:
    body = _base_fdp()
    body["duty_hours"] = "-5"
    response = client.post("/api/v1/ftl/validate-fdp", json=body)
    assert response.status_code == 422


def test_check_returns_per_fdp_verdict(client: TestClient) -> None:
    payload = {
        "fdps": {
            "ref-A": _base_fdp(duty_h=10.0),
            "ref-B": _base_fdp(duty_h=20.0),
        }
    }
    response = client.post("/api/v1/ftl/check", json=payload)
    assert response.status_code == 200, response.text
    verdicts = response.json()["verdicts"]
    assert verdicts["ref-A"]["legality_state"] == "LEGAL"
    assert verdicts["ref-B"]["legality_state"] == "ILLEGAL"


def test_check_rejects_empty_slice(client: TestClient) -> None:
    response = client.post("/api/v1/ftl/check", json={"fdps": {}})
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("report_hour", "expected_band"),
    [(9, "DAY_PEAK"), (5, "EARLY"), (15, "AFTERNOON"), (22, "WOCL")],
)
def test_validate_fdp_band_metadata(
    client: TestClient, report_hour: int, expected_band: str
) -> None:
    body = _base_fdp(hour_local=report_hour, duty_h=8.0)
    response = client.post("/api/v1/ftl/validate-fdp", json=body)
    assert response.status_code == 200, response.text
    trace = response.json()["rule_trace"]
    basic_verdict = next(v for v in trace if v["rule_id"] == "KCAR-P8-FDP-MAX-BASIC")
    assert basic_verdict["metadata"]["band"] == expected_band
