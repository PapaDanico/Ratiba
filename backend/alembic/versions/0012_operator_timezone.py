"""Operator timezone — home-base IANA zone for circadian (WOCL) fatigue scoring."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0012_operator_timezone"
down_revision: str | None = "0011_crew_person_ref"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "operators",
        sa.Column(
            "timezone",
            sa.String(length=64),
            nullable=False,
            server_default="Africa/Nairobi",
        ),
    )


def downgrade() -> None:
    op.drop_column("operators", "timezone")
