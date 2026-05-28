"""Phase 7 — LLM-parsed OM-A constraint sets + human-review workflow.

Revision ID: 0006_constraint_sets
Revises: 0005_notices_and_fleet
Create Date: 2026-05-28

Adds:
- ``constraint_sets`` — one row per parse of an operator's OM-A FTL
  chapter, tied to the OM-A revision number and carrying overall review
  status + coverage against the KCARs baseline.
- ``constraint_rules`` — the per-limit proposals the parser produced, each
  diffed against its baseline value with a per-rule review verdict.
- ``constraint_review_comments`` — the auditable decision trail a crewing
  officer leaves on individual proposed rules.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0006_constraint_sets"
down_revision: str | None = "0005_notices_and_fleet"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "constraint_sets",
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
        sa.Column("om_a_revision", sa.String(64), nullable=False),
        sa.Column("source_filename", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "UNDER_REVIEW",
                "ACCEPTED",
                "REJECTED",
                name="constraint_set_status",
            ),
            nullable=False,
            server_default="UNDER_REVIEW",
        ),
        sa.Column("model", sa.String(64), nullable=True),
        sa.Column("coverage_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("rule_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
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
        "constraint_rules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "constraint_set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("constraint_sets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rule_key", sa.String(128), nullable=False, index=True),
        sa.Column("proposed_value", postgresql.JSONB, nullable=True),
        sa.Column("baseline_value", postgresql.JSONB, nullable=True),
        sa.Column("final_value", postgresql.JSONB, nullable=True),
        sa.Column(
            "review_status",
            sa.Enum(
                "PROPOSED",
                "ACCEPTED",
                "EDITED",
                "REJECTED",
                name="constraint_review_status",
            ),
            nullable=False,
            server_default="PROPOSED",
        ),
        sa.Column("regulation_ref", sa.String(256), nullable=True),
        sa.Column("source_excerpt", sa.Text, nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
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
        "constraint_review_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "constraint_rule_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("constraint_rules.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("constraint_review_comments")
    op.drop_table("constraint_rules")
    op.drop_table("constraint_sets")
    sa.Enum(name="constraint_review_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="constraint_set_status").drop(op.get_bind(), checkfirst=True)
