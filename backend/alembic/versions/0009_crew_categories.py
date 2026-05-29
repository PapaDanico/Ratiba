"""Crew categories: cabin crew + engineer roles, maintenance-auth document.

Adds the new ``crew_role`` enum values (PURSER, CABIN_CREW, ENGINEER) so cabin
crew and accompanying maintenance engineers can be onboarded, and a
``MAINTENANCE_AUTH`` ``document_type`` for engineer type authorisations. The
``crew_category`` discipline is derived from ``role`` in the model, so no
column is added here.

Postgres enum values are additive and cannot be dropped, so ``downgrade`` is a
no-op (the new values simply remain unused).
"""

from __future__ import annotations

from alembic import op

revision: str = "0009_crew_categories"
down_revision: str | None = "0008_crew_documents"
branch_labels: str | None = None
depends_on: str | None = None

_CREW_ROLE_VALUES = ("PURSER", "CABIN_CREW", "ENGINEER")
_DOC_TYPE_VALUES = ("MAINTENANCE_AUTH",)


def upgrade() -> None:
    for value in _CREW_ROLE_VALUES:
        op.execute(f"ALTER TYPE crew_role ADD VALUE IF NOT EXISTS '{value}'")
    for value in _DOC_TYPE_VALUES:
        op.execute(f"ALTER TYPE document_type ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    # Postgres does not support removing enum values; leave them in place.
    pass
