"""Onboarding endpoints — CSV importers for the Plan §5 Phase 6 flow.

All endpoints accept ``multipart/form-data`` with a single ``file`` field
(the CSV) and a query string ``commit=true|false`` for dry-run mode.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.services import imports

router = APIRouter()

Importer = Callable[..., imports.ImportResult]

# Reject oversized uploads before reading them fully into memory — protects a
# small instance from a memory-exhaustion DoS. Generous for any CSV onboarding.
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


def _run(
    importer: Importer,
    session: Session,
    user: User,
    file: UploadFile,
    commit: bool,
) -> dict[str, Any]:
    # Read one byte past the cap so we can detect (not just truncate) overflow.
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"file exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit",
        )
    try:
        result = importer(session, user=user, content=content, commit=commit)
    except imports.ImportError_ as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    body: dict[str, Any] = dict(result.as_dict())
    body["commit"] = commit
    return body


@router.post("/crew", status_code=status.HTTP_200_OK)
def upload_crew(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    commit: bool = Query(default=True),
) -> dict[str, Any]:
    """Required CSV columns: employee_no, first_name, last_name, role,
    date_of_hire, date_of_birth, base_station, contract_type.
    Optional: languages (``;``-separated), faith_observance_flags
    (``;``-separated ``key=value`` pairs).
    """
    return _run(imports.import_crew, session, user, file, commit)


@router.post("/type-ratings", status_code=status.HTTP_200_OK)
def upload_type_ratings(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    commit: bool = Query(default=True),
) -> dict[str, Any]:
    """Required columns: employee_no, aircraft_type, valid_from, valid_until.
    Optional: evidence_ref.
    """
    return _run(imports.import_type_ratings, session, user, file, commit)


@router.post("/currencies", status_code=status.HTTP_200_OK)
def upload_currencies(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    commit: bool = Query(default=True),
) -> dict[str, Any]:
    """Required: employee_no, currency_type, last_completed_date,
    expires_date. Optional: evidence_ref.
    """
    return _run(imports.import_currencies, session, user, file, commit)


@router.post("/historical-fdps", status_code=status.HTTP_200_OK)
def upload_historical_fdps(
    file: UploadFile,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    commit: bool = Query(default=True),
) -> dict[str, Any]:
    """Required: employee_no, date, report_time, off_duty_time,
    sectors_count, flight_hours, duty_hours. Used for the "last 90 days
    of context" import so the cumulative-window FTL rules have history
    on Day 1 of live operation.
    """
    return _run(imports.import_historical_fdps, session, user, file, commit)
