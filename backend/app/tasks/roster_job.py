"""rq worker entrypoint for roster generation.

This module is imported by the rq worker process when a job is dequeued.
It marshals the JSON payload back into :class:`OptimiserInput`, runs the
solver, and returns a JSON-serialisable result dict.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.models.crew import CrewRole
from app.services import optimiser


def payload_to_input(payload: dict[str, Any]) -> optimiser.OptimiserInput:
    return optimiser.OptimiserInput(
        horizon_from=date.fromisoformat(payload["horizon_from"]),
        horizon_to=date.fromisoformat(payload["horizon_to"]),
        crew=tuple(
            optimiser.CrewProfile(
                crew_id=c["crew_id"],
                role=CrewRole(c["role"]),
                type_ratings=tuple(c["type_ratings"]),
                current=c.get("current", True),
                base_tz=c.get("base_tz", "Africa/Nairobi"),
                faith_flags=c.get("faith_flags", {}),
            )
            for c in payload["crew"]
        ),
        sectors=tuple(
            optimiser.SectorInput(
                sector_id=s["sector_id"],
                date_local=date.fromisoformat(s["date_local"]),
                std=datetime.fromisoformat(s["std"]),
                sta=datetime.fromisoformat(s["sta"]),
                aircraft_reg=s["aircraft_reg"],
                aircraft_type=s["aircraft_type"],
                block_hours=Decimal(str(s["block_hours"])),
            )
            for s in payload["sectors"]
        ),
        leave_requests=tuple(
            optimiser.LeaveRequestInput(
                crew_id=r["crew_id"],
                date_from=date.fromisoformat(r["date_from"]),
                date_to=date.fromisoformat(r["date_to"]),
                status=r.get("status", "PENDING"),
            )
            for r in payload.get("leave_requests", [])
        ),
        base_tz=payload.get("base_tz", "Africa/Nairobi"),
        weights={
            **optimiser.DEFAULT_WEIGHTS,
            **payload.get("weights", {}),
        },
        timeout_s=payload.get("timeout_s", 60.0),
    )


def _result_to_dict(r: optimiser.OptimiserResult) -> dict[str, Any]:
    return {
        "status": r.status,
        "assignments": [
            {
                **asdict(a),
                "date_local": a.date_local.isoformat(),
                "sector_ids": list(a.sector_ids),
            }
            for a in r.assignments
        ],
        "objective_value": r.objective_value,
        "unassigned_duty_days": list(r.unassigned_duty_days),
        "diagnostics": r.diagnostics,
        "elapsed_s": r.elapsed_s,
    }


def run_roster_job(payload: dict[str, Any]) -> dict[str, Any]:
    """rq entry point.

    Always returns a dict — never raises — so the queue can store either a
    successful or an error-shaped result without distinguishing.
    """
    try:
        input_ = payload_to_input(payload)
    except Exception as exc:
        return {
            "status": "FAILED",
            "error": f"input deserialisation failed: {exc!r}",
        }

    result = optimiser.solve(input_)
    return _result_to_dict(result)
