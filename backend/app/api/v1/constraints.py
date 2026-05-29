"""Phase 7 — OM-A constraint parser + human-review endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import (
    ConstraintReviewComment,
    ConstraintReviewStatus,
    ConstraintRule,
    ConstraintSet,
    ConstraintSetStatus,
    User,
)
from app.schemas.constraint import (
    ConstraintCommentIn,
    ConstraintCommentOut,
    ConstraintParseIn,
    ConstraintRuleDetail,
    ConstraintRuleOut,
    ConstraintRuleReviewIn,
    ConstraintSetDetail,
    ConstraintSetSummary,
)
from app.services import audit_log, constraint_parser
from app.services.llm_client import LlmClientNotConfigured

router = APIRouter()


def _differs(proposed: object, baseline: object) -> bool:
    return proposed is not None and proposed != baseline


def _rule_out(rule: ConstraintRule) -> ConstraintRuleOut:
    out = ConstraintRuleOut.model_validate(rule)
    out.differs_from_baseline = _differs(rule.proposed_value, rule.baseline_value)
    return out


def _load_set(session: Session, set_id: uuid.UUID, operator_id: uuid.UUID) -> ConstraintSet:
    cset = session.get(ConstraintSet, set_id)
    if cset is None or cset.operator_id != operator_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "constraint set not found")
    return cset


def _load_rule(
    session: Session, set_id: uuid.UUID, rule_id: uuid.UUID, operator_id: uuid.UUID
) -> ConstraintRule:
    _load_set(session, set_id, operator_id)
    rule = session.get(ConstraintRule, rule_id)
    if rule is None or rule.constraint_set_id != set_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "constraint rule not found")
    return rule


@router.post(
    "/parse",
    response_model=ConstraintSetDetail,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def parse_constraint_set(
    payload: ConstraintParseIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConstraintSetDetail:
    try:
        parsed = constraint_parser.parse_om_a(
            payload.om_a_text,
            session=session,
            operator_id=user.operator_id,
        )
    except LlmClientNotConfigured as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LLM parser is not configured (ANTHROPIC_API_KEY missing)",
        ) from exc

    cset = ConstraintSet(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        om_a_revision=payload.om_a_revision,
        source_filename=payload.source_filename,
        status=ConstraintSetStatus.UNDER_REVIEW,
        model=parsed.model,
        coverage_pct=Decimal(str(parsed.coverage_pct)),
        rule_count=len(parsed.rules),
    )
    session.add(cset)
    session.flush()

    for pr in parsed.rules:
        session.add(
            ConstraintRule(
                constraint_set_id=cset.id,
                created_by_user_id=user.id,
                rule_key=pr.rule_key,
                proposed_value=pr.proposed_value,
                baseline_value=pr.baseline_value,
                final_value=None,
                review_status=ConstraintReviewStatus.PROPOSED,
                regulation_ref=pr.regulation_ref,
                source_excerpt=pr.source_excerpt,
                confidence=Decimal(str(pr.confidence)) if pr.confidence is not None else None,
            )
        )

    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="PARSE_OM_A",
        entity_type="constraint_set",
        entity_id=cset.id,
        before_state=None,
        after_state={
            "om_a_revision": payload.om_a_revision,
            "model": parsed.model,
            "coverage_pct": parsed.coverage_pct,
            "rule_count": len(parsed.rules),
        },
    )
    session.commit()
    return _set_detail(session, cset)


def _set_detail(session: Session, cset: ConstraintSet) -> ConstraintSetDetail:
    rules = session.scalars(
        select(ConstraintRule)
        .where(ConstraintRule.constraint_set_id == cset.id)
        .order_by(ConstraintRule.rule_key)
    ).all()
    detail = ConstraintSetDetail.model_validate(cset)
    detail.rules = [_rule_out(r) for r in rules]
    return detail


@router.get("", response_model=list[ConstraintSetSummary])
def list_constraint_sets(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[ConstraintSet]:
    return list(
        session.scalars(
            select(ConstraintSet)
            .where(ConstraintSet.operator_id == user.operator_id)
            .order_by(ConstraintSet.created_at.desc())
        ).all()
    )


@router.get("/{set_id}", response_model=ConstraintSetDetail)
def get_constraint_set(
    set_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConstraintSetDetail:
    cset = _load_set(session, set_id, user.operator_id)
    return _set_detail(session, cset)


@router.get("/{set_id}/rules/{rule_id}", response_model=ConstraintRuleDetail)
def get_constraint_rule(
    set_id: uuid.UUID,
    rule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConstraintRuleDetail:
    rule = _load_rule(session, set_id, rule_id, user.operator_id)
    comments = session.scalars(
        select(ConstraintReviewComment)
        .where(ConstraintReviewComment.constraint_rule_id == rule.id)
        .order_by(ConstraintReviewComment.created_at)
    ).all()
    detail = ConstraintRuleDetail.model_validate(rule)
    detail.differs_from_baseline = _differs(rule.proposed_value, rule.baseline_value)
    detail.comments = [ConstraintCommentOut.model_validate(c) for c in comments]
    return detail


@router.patch(
    "/{set_id}/rules/{rule_id}",
    response_model=ConstraintRuleOut,
    dependencies=[Depends(require_writer)],
)
def review_constraint_rule(
    set_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: ConstraintRuleReviewIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConstraintRuleOut:
    cset = _load_set(session, set_id, user.operator_id)
    if cset.status != ConstraintSetStatus.UNDER_REVIEW:
        raise HTTPException(status.HTTP_409_CONFLICT, "constraint set is no longer under review")
    rule = _load_rule(session, set_id, rule_id, user.operator_id)

    if payload.review_status == ConstraintReviewStatus.EDITED:
        if payload.final_value is None:
            raise HTTPException(422, "EDITED requires final_value")
        rule.final_value = payload.final_value
    elif payload.review_status == ConstraintReviewStatus.ACCEPTED:
        rule.final_value = rule.proposed_value
    elif payload.review_status == ConstraintReviewStatus.REJECTED:
        rule.final_value = rule.baseline_value
    rule.review_status = payload.review_status
    session.flush()

    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="REVIEW_CONSTRAINT_RULE",
        entity_type="constraint_rule",
        entity_id=rule.id,
        before_state=None,
        after_state={"rule_key": rule.rule_key, "review_status": payload.review_status.value},
    )
    session.commit()
    session.refresh(rule)
    return _rule_out(rule)


@router.post(
    "/{set_id}/rules/{rule_id}/comments",
    response_model=ConstraintCommentOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def add_rule_comment(
    set_id: uuid.UUID,
    rule_id: uuid.UUID,
    payload: ConstraintCommentIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConstraintReviewComment:
    rule = _load_rule(session, set_id, rule_id, user.operator_id)
    comment = ConstraintReviewComment(
        constraint_rule_id=rule.id,
        user_id=user.id,
        body=payload.body,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.post(
    "/{set_id}/accept", response_model=ConstraintSetDetail, dependencies=[Depends(require_writer)]
)
def accept_constraint_set(
    set_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ConstraintSetDetail:
    cset = _load_set(session, set_id, user.operator_id)
    if cset.status != ConstraintSetStatus.UNDER_REVIEW:
        raise HTTPException(status.HTTP_409_CONFLICT, "constraint set is no longer under review")

    pending = session.scalars(
        select(ConstraintRule).where(
            ConstraintRule.constraint_set_id == cset.id,
            ConstraintRule.review_status == ConstraintReviewStatus.PROPOSED,
            ConstraintRule.proposed_value.isnot(None),
        )
    ).all()
    if pending:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{len(pending)} proposed rule(s) still need review before acceptance",
        )

    cset.status = ConstraintSetStatus.ACCEPTED
    cset.accepted_at = datetime.now(UTC)
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="ACCEPT_CONSTRAINT_SET",
        entity_type="constraint_set",
        entity_id=cset.id,
        before_state=None,
        after_state={"om_a_revision": cset.om_a_revision},
    )
    session.commit()
    return _set_detail(session, cset)
