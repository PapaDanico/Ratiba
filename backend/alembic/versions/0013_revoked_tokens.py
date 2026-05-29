"""Revoked refresh-token registry (rotation + logout revocation)."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0013_revoked_tokens"
down_revision: str | None = "0012_operator_timezone"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "revoked_tokens",
        sa.Column("jti", sa.String(length=64), primary_key=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("revoked_tokens")
