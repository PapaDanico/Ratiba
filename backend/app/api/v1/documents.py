"""Crew document management — licences, medicals, passports, visas.

Stores document metadata with an expiry date that feeds the recurrency
tracker. File bytes aren't uploaded here; ``file_ref`` holds a link/path
to wherever the operator keeps the scan.
"""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import Crew, CrewDocument, User
from app.schemas.document import DocumentIn, DocumentOut
from app.services import audit_log

router = APIRouter()

AMBER_THRESHOLD_DAYS = 30


def _state(expiry: date | None) -> tuple[int | None, str]:
    if expiry is None:
        return None, "NA"
    days = (expiry - date.today()).days
    if days < 0:
        return days, "RED"
    if days <= AMBER_THRESHOLD_DAYS:
        return days, "AMBER"
    return days, "GREEN"


def _to_out(doc: CrewDocument, crew: Crew | None) -> DocumentOut:
    days, state = _state(doc.expiry_date)
    return DocumentOut(
        id=doc.id,
        crew_id=doc.crew_id,
        employee_no=crew.employee_no if crew else "—",
        crew_name=f"{crew.first_name} {crew.last_name}" if crew else "—",
        doc_type=doc.doc_type,
        document_number=doc.document_number,
        issuing_authority=doc.issuing_authority,
        issue_date=doc.issue_date,
        expiry_date=doc.expiry_date,
        file_ref=doc.file_ref,
        notes=doc.notes,
        days_remaining=days,
        state=state,
    )


def _crew_map(session: Session, operator_id: uuid.UUID) -> dict[uuid.UUID, Crew]:
    crew = session.scalars(select(Crew).where(Crew.operator_id == operator_id)).all()
    return {c.id: c for c in crew}


@router.get("", response_model=list[DocumentOut])
def list_documents(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[DocumentOut]:
    crew_by_id = _crew_map(session, user.operator_id)
    rows = session.scalars(
        select(CrewDocument)
        .where(CrewDocument.operator_id == user.operator_id)
        .order_by(CrewDocument.expiry_date.is_(None), CrewDocument.expiry_date)
    ).all()
    return [_to_out(d, crew_by_id.get(d.crew_id)) for d in rows]


@router.post(
    "/crew/{crew_id}",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_document(
    crew_id: uuid.UUID,
    payload: DocumentIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> DocumentOut:
    if payload.expiry_date and payload.issue_date and payload.expiry_date < payload.issue_date:
        raise HTTPException(status_code=422, detail="expiry_date before issue_date")
    crew = session.scalar(
        select(Crew).where(Crew.id == crew_id).where(Crew.operator_id == user.operator_id)
    )
    if crew is None:
        raise HTTPException(status_code=404, detail="crew not found")
    doc = CrewDocument(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        crew_id=crew_id,
        doc_type=payload.doc_type,
        document_number=payload.document_number,
        issuing_authority=payload.issuing_authority,
        issue_date=payload.issue_date,
        expiry_date=payload.expiry_date,
        file_ref=payload.file_ref,
        notes=payload.notes,
    )
    session.add(doc)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="ADD_DOCUMENT",
        entity_type="crew_document",
        entity_id=doc.id,
        before_state=None,
        after_state=payload.model_dump(mode="json"),
    )
    session.commit()
    session.refresh(doc)
    return _to_out(doc, crew)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    doc = session.scalar(
        select(CrewDocument)
        .where(CrewDocument.id == document_id)
        .where(CrewDocument.operator_id == user.operator_id)
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="document not found")
    session.delete(doc)
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="DELETE_DOCUMENT",
        entity_type="crew_document",
        entity_id=document_id,
        before_state={"doc_type": doc.doc_type.value, "crew_id": str(doc.crew_id)},
        after_state=None,
    )
    session.commit()
