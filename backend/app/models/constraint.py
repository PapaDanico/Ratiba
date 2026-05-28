"""Phase 7 — LLM-parsed OM-A constraint sets + human-review workflow.

A :class:`ConstraintSet` is one parse of an operator's OM-A FTL chapter.
It owns a list of :class:`ConstraintRule` rows — one per FTL limit the
parser proposed — each carrying the proposed value, the KCARs baseline it
diffs against, and a per-rule review verdict. :class:`ConstraintReviewComment`
gives the crewing officer an auditable decision trail on each rule.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import OperatorScopedMixin, TimestampMixin, UUIDMixin


class ConstraintSetStatus(enum.StrEnum):
    UNDER_REVIEW = "UNDER_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ConstraintReviewStatus(enum.StrEnum):
    PROPOSED = "PROPOSED"  # parser output, untouched
    ACCEPTED = "ACCEPTED"  # officer took the proposed value as-is
    EDITED = "EDITED"  # officer overrode with final_value
    REJECTED = "REJECTED"  # officer kept the baseline, discarded the proposal


class ConstraintSet(UUIDMixin, TimestampMixin, OperatorScopedMixin, Base):
    __tablename__ = "constraint_sets"

    om_a_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[ConstraintSetStatus] = mapped_column(
        SAEnum(ConstraintSetStatus, name="constraint_set_status"),
        nullable=False,
        default=ConstraintSetStatus.UNDER_REVIEW,
    )
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    coverage_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    rule_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConstraintRule(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "constraint_rules"

    constraint_set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("constraint_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # none_as_null so a missing proposal is SQL NULL, not JSON 'null' — the
    # acceptance gate filters on "has a proposal" via IS NOT NULL.
    proposed_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    baseline_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    final_value: Mapped[Any] = mapped_column(JSONB(none_as_null=True), nullable=True)
    review_status: Mapped[ConstraintReviewStatus] = mapped_column(
        SAEnum(ConstraintReviewStatus, name="constraint_review_status"),
        nullable=False,
        default=ConstraintReviewStatus.PROPOSED,
    )
    regulation_ref: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)


class ConstraintReviewComment(UUIDMixin, Base):
    __tablename__ = "constraint_review_comments"

    constraint_rule_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("constraint_rules.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
