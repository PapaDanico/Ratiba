"""Crew document model: licences, medicals, passports, visas, etc.

Stores document *metadata* (type, number, issuing authority, issue/expiry
dates, and an optional reference to a stored file) rather than the file
bytes themselves. The expiry_date feeds the recurrency tracker so nothing
lapses unnoticed — the highest-value reason small operators want document
management.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class DocumentType(enum.StrEnum):
    LICENCE = "LICENCE"  # CPL / ATPL
    MEDICAL = "MEDICAL"  # Class 1 / 2
    TYPE_RATING_CERT = "TYPE_RATING_CERT"
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    WORK_PERMIT = "WORK_PERMIT"
    OTHER = "OTHER"


class CrewDocument(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "crew_documents"

    crew_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("crew.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[DocumentType] = mapped_column(
        SAEnum(DocumentType, name="document_type"), nullable=False
    )
    document_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issuing_authority: Mapped[str | None] = mapped_column(String(128), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    file_ref: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
