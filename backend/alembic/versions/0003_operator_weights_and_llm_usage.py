"""Phase 4.5 — operator soft-weight overrides + LLM usage telemetry table.

Revision ID: 0003_operator_weights
Revises: 0002_pilot_pairing
Create Date: 2026-05-28

Closes two Phase 2/4 deferrals:

- Operators can persist their preferred objective-function weights so the
  dashboard's "Generate roster" calls don't have to re-specify them.
- LLM usage is logged per call to ``llm_usage_events`` so Phase 6 can
  aggregate cost against the Plan §5 Phase 4 ≤ USD 2 / pilot / month target.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_operator_weights"
down_revision: str | None = "0002_pilot_pairing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "operators",
        sa.Column(
            "default_soft_weights",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )

    op.create_table(
        "llm_usage_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "operator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operators.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("call_site", sa.String(64), nullable=False, index=True),
        sa.Column("model", sa.String(64), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False),
        sa.Column("output_tokens", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("llm_usage_events")
    op.drop_column("operators", "default_soft_weights")
