"""Roster endpoints — Phase 2 (generate / jobs / explain) and Phase 3 (get / publish)."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.job_queue import JobQueue, get_job_queue
from app.models import User
from app.schemas.roster import (
    AmendRosterRequest,
    AmendRosterResponse,
    AssignmentOut,
    AutoGenerateRosterRequest,
    AutoGenerateRosterResponse,
    ConstraintBindingOut,
    ExplainRequest,
    ExplainResponse,
    GenerateRosterAcceptedResponse,
    GenerateRosterRequest,
    JobStatusResponse,
    PublishRosterRequest,
    PublishRosterResponse,
    RosterResult,
)
from app.services import auto_roster, optimiser, roster_service
from app.services.crew_roster_pdf import CrewRosterPdfError, generate_crew_roster_pdf
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


@router.post(
    "/auto-generate",
    response_model=AutoGenerateRosterResponse,
    summary="Build a draft roster from stored crew + schedule (one click)",
)
def auto_generate(
    payload: AutoGenerateRosterRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AutoGenerateRosterResponse:
    if payload.horizon_to < payload.horizon_from:
        raise HTTPException(status_code=422, detail="horizon_to before horizon_from")
    result, sectors = auto_roster.build_auto_roster(
        session,
        operator_id=user.operator_id,
        horizon_from=payload.horizon_from,
        horizon_to=payload.horizon_to,
        base_tz=payload.base_tz,
        timeout_s=payload.timeout_s,
    )
    return AutoGenerateRosterResponse(
        result=RosterResult(
            status=result.status,
            assignments=[
                AssignmentOut(
                    duty_day_key=a.duty_day_key,
                    date_local=a.date_local,
                    aircraft_reg=a.aircraft_reg,
                    aircraft_type=a.aircraft_type,
                    sector_ids=list(a.sector_ids),
                    captain_id=a.captain_id,
                    fo_id=a.fo_id,
                )
                for a in result.assignments
            ],
            objective_value=result.objective_value,
            unassigned_duty_days=list(result.unassigned_duty_days),
            diagnostics=result.diagnostics,
            elapsed_s=result.elapsed_s,
        ),
        sectors=sectors,
    )


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


@router.get(
    "",
    response_model=list[AssignmentOut],
    summary="List published duty-day assignments within a date range",
)
def get_roster(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[AssignmentOut]:
    return roster_service.list_published_assignments(
        session,
        operator_id=user.operator_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.post(
    "/publish",
    response_model=PublishRosterResponse,
    summary="Publish a roster — writes SectorAssignment + FlightDutyPeriod rows",
)
def publish(
    payload: PublishRosterRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> PublishRosterResponse:
    try:
        return roster_service.publish_roster(session, user=user, payload=payload)
    except roster_service.RosterPersistenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/amend",
    response_model=AmendRosterResponse,
    summary="Replace the crew on a single published duty day, with reason",
)
def amend(
    payload: AmendRosterRequest,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> AmendRosterResponse:
    try:
        captain_id, fo_id, legality = roster_service.amend_roster(
            session,
            user=user,
            duty_day_key=payload.duty_day_key,
            new_captain_employee_no=payload.new_captain_employee_no,
            new_fo_employee_no=payload.new_fo_employee_no,
            reason=payload.reason,
        )
    except roster_service.RosterPersistenceError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AmendRosterResponse(
        duty_day_key=payload.duty_day_key,
        captain_id=str(captain_id),
        fo_id=str(fo_id),
        legality_state=legality.value,
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


@router.get(
    "/crew/{crew_id}/monthly-pdf",
    summary="Download monthly roster PDF for a single crew member",
    response_class=StreamingResponse,
)
def crew_monthly_pdf(
    crew_id: uuid.UUID,
    year: int = Query(..., ge=2020, le=2040),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    try:
        pdf_bytes = generate_crew_roster_pdf(
            session,
            operator_id=user.operator_id,
            crew_id=crew_id,
            year=year,
            month=month,
        )
    except CrewRosterPdfError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filename = f"roster_{crew_id}_{year}-{month:02d}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
