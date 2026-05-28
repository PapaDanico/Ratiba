"""Phase 5 — KCAA audit pack storage.

Revision ID: 0004_audit_packs
Revises: 0003_operator_weights
Create Date: 2026-05-28

The PDF bytes live on disk under ``backend/audit_packs/`` (or
``AUDIT_PACK_DIR``) for the MVP; Phase 6 swaps storage to S3-compatible
object storage. The DB row carries metadata + the SHA-256 of the PDF so
the verification endpoint can prove tamper-evidence without reading the
bytes back.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_audit_packs"
down_revision: str | None = "0003_operator_weights"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_packs",
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
        sa.Column("period_from", sa.Date, nullable=False),
        sa.Column("period_to", sa.Date, nullable=False),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("sha256_hex", sa.String(64), nullable=False, unique=True),
        sa.Column("byte_size", sa.Integer, nullable=False),
        sa.Column("generator_version", sa.String(64), nullable=False),
        sa.Column("crew_count", sa.Integer, nullable=False),
        sa.Column("fdp_count", sa.Integer, nullable=False),
        sa.Column("anomaly_count", sa.Integer, nullable=False),
        sa.Column(
            "created_at",
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
    op.drop_table("audit_packs")
