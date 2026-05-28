"""Phase 7 — OM-A constraint-set parse + review schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.constraint import ConstraintReviewStatus, ConstraintSetStatus


class ConstraintParseIn(BaseModel):
    om_a_revision: str = Field(min_length=1, max_length=64)
    om_a_text: str = Field(min_length=1)
    source_filename: str | None = Field(default=None, max_length=512)


class ConstraintRuleReviewIn(BaseModel):
    review_status: ConstraintReviewStatus
    final_value: Any | None = None


class ConstraintCommentIn(BaseModel):
    body: str = Field(min_length=1)


class ConstraintCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    body: str
    created_at: datetime


class ConstraintRuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rule_key: str
    proposed_value: Any | None
    baseline_value: Any | None
    final_value: Any | None
    review_status: ConstraintReviewStatus
    regulation_ref: str | None
    source_excerpt: str | None
    confidence: Decimal | None
    # True when the parser proposed something different from the baseline —
    # the rules a reviewer should actually look at first.
    differs_from_baseline: bool = False


class ConstraintRuleDetail(ConstraintRuleOut):
    comments: list[ConstraintCommentOut] = []


class ConstraintSetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    om_a_revision: str
    source_filename: str | None
    status: ConstraintSetStatus
    model: str | None
    coverage_pct: Decimal | None
    rule_count: int
    accepted_at: datetime | None
    created_at: datetime


class ConstraintSetDetail(ConstraintSetSummary):
    rules: list[ConstraintRuleOut] = []
