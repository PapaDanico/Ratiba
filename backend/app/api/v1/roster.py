"""Roster generation endpoints — Phase 2.

- ``POST /api/v1/roster/generate`` — enqueue an async optimiser run
- ``GET  /api/v1/roster/jobs/{job_id}`` — fetch status + result
- ``POST /api/v1/roster/explain`` — return binding constraints for a duty day

Persistence of the resulting roster (and the ``audit_event`` row that
goes with it) lands later in Phase 2 once the dashboard's publish flow
is built out in Phase 3.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.job_queue import JobQueue, get_job_queue
from app.schemas.roster import (
    ConstraintBindingOut,
    ExplainRequest,
    ExplainResponse,
    GenerateRosterAcceptedResponse,
    GenerateRosterRequest,
    JobStatusResponse,
    RosterResult,
)
from app.services import optimiser
from app.tasks.roster_job import payload_to_input

router = APIRouter()


def _payload_to_dict(payload: GenerateRosterRequest) -> dict[str, object]:
    """JSON-roundtrip the Pydantic payload so the rq worker gets pure data."""
    return payload.model_dump(mode="json")


@router.post(
    "/generate",
    response_model=GenerateRosterAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue an optimiser run; returns job_id",
)
async def generate(
    payload: GenerateRosterRequest,
    queue: JobQueue = Depends(get_job_queue),
) -> GenerateRosterAcceptedResponse:
    job = queue.enqueue(
        "app.tasks.roster_job.run_roster_job",
        _payload_to_dict(payload),
    )
    return GenerateRosterAcceptedResponse(job_id=job.id, status=job.status)


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll a roster job by id",
)
async def get_job(
    job_id: str,
    queue: JobQueue = Depends(get_job_queue),
) -> JobStatusResponse:
    record = queue.fetch(job_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"job {job_id} not found")

    result: RosterResult | None = None
    if record.result is not None and record.status == "FINISHED":
        result = RosterResult.model_validate(record.result)

    return JobStatusResponse(
        job_id=record.id,
        status=record.status,
        result=result,
        error=record.error,
    )


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Binding constraints for a single duty day",
)
async def explain(payload: ExplainRequest) -> ExplainResponse:
    explanation = optimiser.explain(
        payload_to_input(_payload_to_dict(payload.input)),
        payload.duty_day_key,
    )
    return ExplainResponse(
        duty_day_key=explanation.duty_day_key,
        captain_id=explanation.captain_id,
        fo_id=explanation.fo_id,
        bindings=[
            ConstraintBindingOut(
                rule_id=b.rule_id,
                description=b.description,
                metadata=b.metadata,
            )
            for b in explanation.bindings
        ],
    )
