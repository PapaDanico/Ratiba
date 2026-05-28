"""Operational exports — payroll CSV (more report formats land here later)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.services import payroll

router = APIRouter()


@router.get(
    "/payroll.csv",
    summary="Per-crew duty + block hours for a pay period (CSV)",
    response_class=StreamingResponse,
)
def payroll_csv(
    date_from: date = Query(...),
    date_to: date = Query(...),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> StreamingResponse:
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="date_to before date_from")
    rows = payroll.build_rows(
        session,
        operator_id=user.operator_id,
        date_from=date_from,
        date_to=date_to,
    )
    body = payroll.to_csv(rows)
    filename = f"payroll_{date_from.isoformat()}_{date_to.isoformat()}.csv"
    return StreamingResponse(
        iter([body]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
