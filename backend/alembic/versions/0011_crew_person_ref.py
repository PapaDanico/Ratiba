"""Crew person_ref — stable cross-operator identity (e.g. licence number)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0011_crew_person_ref"
down_revision: str | None = "0010_postings"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column("crew", sa.Column("person_ref", sa.String(length=64), nullable=True))
    op.create_index("ix_crew_person_ref", "crew", ["person_ref"])


def downgrade() -> None:
    op.drop_index("ix_crew_person_ref", table_name="crew")
    op.drop_column("crew", "person_ref")
