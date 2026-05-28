"""Crew contact channels — email + phone for outbound messaging.

Revision ID: 0007_crew_contact_channels
Revises: 0006_constraint_sets
Create Date: 2026-05-28

Adds two optional contact fields to crew:
- ``email`` — for SMTP-based notice delivery.
- ``phone_number`` — for Africa's Talking SMS (E.164 format, e.g. +254712345678).

Both are nullable: crew with neither simply receive notices via Telegram
(existing channel) and the /crew/me web view.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_crew_contact_channels"
down_revision: str | None = "0006_constraint_sets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("crew", sa.Column("email", sa.String(255), nullable=True, index=True))
    op.add_column("crew", sa.Column("phone_number", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("crew", "phone_number")
    op.drop_column("crew", "email")
