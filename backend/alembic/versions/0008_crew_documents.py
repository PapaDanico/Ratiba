"""Crew documents: licences, medicals, passports, visas with expiry tracking.

Revision ID: 0008_crew_documents
Revises: 0007_crew_contact_channels
Create Date: 2026-05-28

Adds ``crew_documents`` — operator-scoped metadata for each crew member's
regulatory and travel documents. The expiry_date is indexed because it
drives the recurrency / expiry-alert view.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0008_crew_documents"
down_revision: str | None = "0007_crew_contact_channels"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    document_type = postgresql.ENUM(
        "LICENCE",
        "MEDICAL",
        "TYPE_RATING_CERT",
        "PASSPORT",
        "VISA",
        "WORK_PERMIT",
        "OTHER",
        name="document_type",
        create_type=False,
    )
    bind = op.get_bind()
    document_type.create(bind, checkfirst=True)

    op.create_table(
        "crew_documents",
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
        sa.Column("doc_type", document_type, nullable=False),
        sa.Column("document_number", sa.String(128), nullable=True),
        sa.Column("issuing_authority", sa.String(128), nullable=True),
        sa.Column("issue_date", sa.Date, nullable=True),
        sa.Column("expiry_date", sa.Date, nullable=True, index=True),
        sa.Column("file_ref", sa.String(1024), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
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
    op.drop_table("crew_documents")
    op.execute("DROP TYPE IF EXISTS document_type")
