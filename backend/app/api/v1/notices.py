"""Notice (crew comms) endpoints — Crewing-Officer authoring side."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_writer
from app.models import Crew, Notice, NoticeAcknowledgement, User
from app.models.notice import NoticeCategory
from app.schemas.notice import NoticeIn, NoticeOut, NoticePatch, NoticeWithAckStats
from app.services import audit_log, notify

router = APIRouter()


@router.post(
    "",
    response_model=NoticeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_writer)],
)
def create_notice(
    payload: NoticeIn,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> NoticeOut:
    notice = Notice(
        operator_id=user.operator_id,
        created_by_user_id=user.id,
        category=payload.category,
        severity=payload.severity,
        title=payload.title,
        body=payload.body,
        image_url=payload.image_url,
        requires_ack=payload.requires_ack,
        pinned=payload.pinned,
        published=payload.published,
        published_at=datetime.now(UTC) if payload.published else None,
        expires_at=payload.expires_at,
    )
    session.add(notice)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="CREATE_NOTICE",
        entity_type="notice",
        entity_id=notice.id,
        before_state=None,
        after_state={
            "category": payload.category.value,
            "severity": payload.severity.value,
            "title": payload.title,
            "published": payload.published,
        },
    )
    session.commit()
    session.refresh(notice)

    if notice.published:
        pushed = notify.push_notice(session, notice)
        if pushed:
            # Telemetry only — the notice already persisted.
            audit_log.record(
                session,
                operator_id=user.operator_id,
                actor_user_id=user.id,
                action="PUSH_NOTICE",
                entity_type="notice",
                entity_id=notice.id,
                before_state=None,
                after_state={"telegram_sends": pushed},
            )
            session.commit()
    return NoticeOut.model_validate(notice)


@router.get("", response_model=list[NoticeWithAckStats])
def list_notices(
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    category: NoticeCategory | None = Query(default=None),
) -> list[NoticeWithAckStats]:
    q = select(Notice).where(Notice.operator_id == user.operator_id)
    if category is not None:
        q = q.where(Notice.category == category)
    q = q.order_by(Notice.pinned.desc(), Notice.created_at.desc())
    notices = session.scalars(q).all()

    crew_total = (
        session.scalar(
            select(func.count())
            .select_from(Crew)
            .where(Crew.operator_id == user.operator_id)
            .where(Crew.active.is_(True))
        )
        or 0
    )

    out: list[NoticeWithAckStats] = []
    for n in notices:
        ack_count = (
            session.scalar(
                select(func.count())
                .select_from(NoticeAcknowledgement)
                .where(NoticeAcknowledgement.notice_id == n.id)
            )
            or 0
        )
        item = NoticeWithAckStats.model_validate(n)
        item.ack_count = ack_count
        item.crew_total = crew_total
        out.append(item)
    return out


@router.patch("/{notice_id}", response_model=NoticeOut, dependencies=[Depends(require_writer)])
def update_notice(
    notice_id: uuid.UUID,
    payload: NoticePatch,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> NoticeOut:
    notice = session.scalar(
        select(Notice).where(Notice.id == notice_id).where(Notice.operator_id == user.operator_id)
    )
    if notice is None:
        raise HTTPException(status_code=404, detail="notice not found")

    was_published = notice.published
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(notice, k, v)
    # Stamp published_at on first publish.
    if not was_published and notice.published and notice.published_at is None:
        notice.published_at = datetime.now(UTC)
    session.flush()
    audit_log.record(
        session,
        operator_id=user.operator_id,
        actor_user_id=user.id,
        action="UPDATE_NOTICE",
        entity_type="notice",
        entity_id=notice.id,
        before_state={"published": was_published},
        after_state={"published": notice.published},
    )
    session.commit()
    session.refresh(notice)

    if not was_published and notice.published:
        notify.push_notice(session, notice)
    return NoticeOut.model_validate(notice)
