"""Notices (crew comms) + per-operator aircraft fleet registry.

Revision ID: 0005_notices_and_fleet
Revises: 0004_audit_packs
Create Date: 2026-05-28

Adds:
- ``notices`` — operator-scoped crew communications (operational, fleet,
  safety, social/morale) with severity, optional ack requirement, and an
  optional image URL for lighter morale posts.
- ``notice_acknowledgements`` — per-crew read receipts for notices that
  require acknowledgement.
- ``aircraft`` — the operator's fleet registry. Each aircraft has a
  registration + an aircraft_type chosen from the curated reference list.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0005_notices_and_fleet"
down_revision: str | None = "0004_audit_packs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    notice_category = postgresql.ENUM(
        "OPERATIONAL",
        "FLEET",
        "SAFETY",
        "SOCIAL",
        name="notice_category",
        create_type=False,
    )
    notice_severity = postgresql.ENUM(
        "INFO", "IMPORTANT", "CRITICAL", name="notice_severity", create_type=False
    )
    bind = op.get_bind()
    notice_category.create(bind, checkfirst=True)
    notice_severity.create(bind, checkfirst=True)

    op.create_table(
        "notices",
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
        sa.Column("category", notice_category, nullable=False),
        sa.Column("severity", notice_severity, nullable=False, server_default="INFO"),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("image_url", sa.String(1024), nullable=True),
        sa.Column("requires_ack", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("published", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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

    op.create_table(
        "notice_acknowledgements",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "notice_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("notices.id", ondelete="CASCADE"),
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
        sa.Column(
            "acknowledged_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("notice_id", "crew_id", name="uq_notice_ack_notice_crew"),
    )

    op.create_table(
        "aircraft",
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
        sa.Column("registration", sa.String(16), nullable=False),
        sa.Column("aircraft_type", sa.String(32), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
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
        sa.UniqueConstraint(
            "operator_id", "registration", name="uq_aircraft_operator_registration"
        ),
    )


def downgrade() -> None:
    op.drop_table("aircraft")
    op.drop_table("notice_acknowledgements")
    op.drop_table("notices")
    op.execute("DROP TYPE IF EXISTS notice_severity")
    op.execute("DROP TYPE IF EXISTS notice_category")
