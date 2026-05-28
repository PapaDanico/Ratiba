"""Phase 4 — pilot pairing + Telegram chat id

Revision ID: 0002_pilot_pairing
Revises: 0001_initial
Create Date: 2026-05-28

Adds:
- ``crew.telegram_chat_id`` so the bot can recognise a paired pilot
- ``pairing_tokens`` table — short-lived single-use codes the dashboard
  issues to a pilot, redeemed by the bot or the /crew/me web view
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_pilot_pairing"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "crew",
        sa.Column("telegram_chat_id", sa.BigInteger, nullable=True, unique=False),
    )
    op.create_index(
        "ix_crew_telegram_chat_id",
        "crew",
        ["telegram_chat_id"],
        unique=False,
    )

    op.create_table(
        "pairing_tokens",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "operator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operators.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("code", sa.String(16), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_telegram_chat_id", sa.BigInteger, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("pairing_tokens")
    op.drop_index("ix_crew_telegram_chat_id", table_name="crew")
    op.drop_column("crew", "telegram_chat_id")
