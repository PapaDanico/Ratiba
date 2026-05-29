"""Outstation / ACMI postings: postings + posting_assignments tables."""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0010_postings"
down_revision: str | None = "0009_crew_categories"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    posting_type = sa.Enum("ACMI_WET_LEASE", "DETACHMENT", "TRAINING", name="posting_type")
    op.create_table(
        "postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("location_icao", sa.String(length=8), nullable=False),
        sa.Column("country", sa.String(length=64), nullable=False),
        sa.Column("base_tz", sa.String(length=64), nullable=False),
        sa.Column("type", posting_type, nullable=False),
        sa.Column("lessee_name", sa.String(length=128), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False, index=True),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "posting_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("posting_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("crew_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["posting_id"], ["postings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["crew_id"], ["crew.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("posting_id", "crew_id", name="uq_posting_assignment"),
    )


def downgrade() -> None:
    op.drop_table("posting_assignments")
    op.drop_table("postings")
    sa.Enum(name="posting_type").drop(op.get_bind(), checkfirst=True)
