"""Notice (crew comms) schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.notice import NoticeCategory, NoticeSeverity


class NoticeIn(BaseModel):
    category: NoticeCategory
    severity: NoticeSeverity = NoticeSeverity.INFO
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(min_length=1)
    image_url: str | None = Field(default=None, max_length=1024)
    requires_ack: bool = False
    pinned: bool = False
    published: bool = True
    expires_at: datetime | None = None


class NoticePatch(BaseModel):
    title: str | None = Field(default=None, max_length=256)
    body: str | None = None
    severity: NoticeSeverity | None = None
    image_url: str | None = Field(default=None, max_length=1024)
    requires_ack: bool | None = None
    pinned: bool | None = None
    published: bool | None = None
    expires_at: datetime | None = None


class NoticeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: NoticeCategory
    severity: NoticeSeverity
    title: str
    body: str
    image_url: str | None
    requires_ack: bool
    published: bool
    pinned: bool
    published_at: datetime | None
    expires_at: datetime | None
    created_at: datetime


class NoticeWithAckStats(NoticeOut):
    ack_count: int = 0
    crew_total: int = 0


class PilotNoticeOut(NoticeOut):
    acknowledged: bool = False
