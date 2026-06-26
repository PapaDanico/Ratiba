"""crew whatsapp number

Revision ID: 0014_crew_whatsapp
Revises: 0013_revoked_tokens

Adds an opt-in WhatsApp number to crew so the notify service can deliver via
Africa's Talking WhatsApp, kept separate from ``phone_number`` (SMS) so the two
channels don't double-message the same person.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0014_crew_whatsapp"
down_revision = "0013_revoked_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crew", sa.Column("whatsapp_number", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("crew", "whatsapp_number")
