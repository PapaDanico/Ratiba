"""Crew document schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.document import DocumentType


class DocumentIn(BaseModel):
    doc_type: DocumentType
    document_number: str | None = Field(default=None, max_length=128)
    issuing_authority: str | None = Field(default=None, max_length=128)
    issue_date: date | None = None
    expiry_date: date | None = None
    file_ref: str | None = Field(default=None, max_length=1024)
    notes: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    crew_id: uuid.UUID
    employee_no: str
    crew_name: str
    doc_type: DocumentType
    document_number: str | None
    issuing_authority: str | None
    issue_date: date | None
    expiry_date: date | None
    file_ref: str | None
    notes: str | None
    days_remaining: int | None  # None when the document has no expiry
    state: str  # GREEN | AMBER | RED | NA
