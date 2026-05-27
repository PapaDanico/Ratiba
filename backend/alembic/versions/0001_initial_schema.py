"""Initial schema — all Section 4 entities.

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27

Creates: operators, users, crew, crew_type_ratings, crew_currencies,
flight_duty_periods, sectors, sector_assignments, leave_requests,
swap_requests, ftl_rules, audit_events.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Reusable column lists --------------------------------------------------------


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def _operator_scope() -> sa.Column:
    return sa.Column(
        "operator_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("operators.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )


# Upgrade ----------------------------------------------------------------------


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # Define every ENUM once with create_type=False so column references
    # don't re-emit empty CREATE TYPE statements. We create each type
    # explicitly below before any table uses it.
    operator_tier = postgresql.ENUM(
        "ENTRY", "STANDARD", "PLUS", name="operator_tier", create_type=False
    )
    user_role = postgresql.ENUM(
        "CREWING_OFFICER",
        "CHIEF_PILOT",
        "ADMIN",
        "PILOT",
        name="user_role",
        create_type=False,
    )
    crew_role = postgresql.ENUM("CAPT", "FO", "SO", name="crew_role", create_type=False)
    contract_type = postgresql.ENUM(
        "FULL_TIME",
        "CONTRACT",
        "FREELANCE",
        name="contract_type",
        create_type=False,
    )
    currency_type = postgresql.ENUM(
        "LANDINGS_90D",
        "ROUTE_FAM",
        "MEL_COMP",
        "LINE_CHECK",
        "OPC",
        "LPC",
        "EMERG_PROC",
        "FIRST_AID",
        "DG",
        "CRM",
        "SEC_TRAINING",
        name="currency_type",
        create_type=False,
    )
    sector_status = postgresql.ENUM(
        "PLANNED",
        "PUBLISHED",
        "OPERATING",
        "COMPLETED",
        "CANCELLED",
        name="sector_status",
        create_type=False,
    )
    fdp_type = postgresql.ENUM(
        "FDP",
        "STANDBY",
        "POSITIONING",
        "TRAINING",
        "OFF",
        "LEAVE",
        "SICK",
        name="fdp_type",
        create_type=False,
    )
    legality_state = postgresql.ENUM(
        "LEGAL",
        "AT_LIMIT",
        "REQUIRES_FRMS_DEROGATION",
        "ILLEGAL",
        name="legality_state",
        create_type=False,
    )
    rule_source = postgresql.ENUM(
        "MANUAL_REVIEW",
        "LLM_PARSED",
        "OM_A_REVISION_X",
        name="rule_source",
        create_type=False,
    )
    leave_type = postgresql.ENUM(
        "ANNUAL",
        "SICK",
        "COMPASSIONATE",
        "FAITH",
        "OTHER",
        name="leave_type",
        create_type=False,
    )
    leave_status = postgresql.ENUM(
        "PENDING", "APPROVED", "REJECTED", name="leave_status", create_type=False
    )
    swap_status = postgresql.ENUM(
        "PENDING",
        "APPROVED",
        "REJECTED",
        "CANCELLED",
        name="swap_status",
        create_type=False,
    )

    bind = op.get_bind()
    for enum_type in (
        operator_tier,
        user_role,
        crew_role,
        contract_type,
        currency_type,
        sector_status,
        fdp_type,
        legality_state,
        rule_source,
        leave_type,
        leave_status,
        swap_status,
    ):
        enum_type.create(bind, checkfirst=True)

    # operators -----------------------------------------------------------------
    op.create_table(
        "operators",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("aoc_number", sa.String(64), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("base", sa.String(8), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("tier", operator_tier, nullable=False, server_default="ENTRY"),
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
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )

    # users ---------------------------------------------------------------------
    op.create_table(
        "users",
        _uuid_pk(),
        _operator_scope(),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        *_timestamps(),
    )

    # crew ----------------------------------------------------------------------
    op.create_table(
        "crew",
        _uuid_pk(),
        _operator_scope(),
        sa.Column("employee_no", sa.String(32), nullable=False),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("last_name", sa.String(128), nullable=False),
        sa.Column("role", crew_role, nullable=False),
        sa.Column("date_of_hire", sa.Date, nullable=False),
        sa.Column("date_of_birth", sa.Date, nullable=False),
        sa.Column("base_station", sa.String(8), nullable=False),
        sa.Column("contract_type", contract_type, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "languages",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "faith_observance_flags",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        *_timestamps(),
        sa.UniqueConstraint("operator_id", "employee_no", name="uq_crew_operator_employee_no"),
    )

    # crew_type_ratings ---------------------------------------------------------
    op.create_table(
        "crew_type_ratings",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("aircraft_type", sa.String(32), nullable=False),
        sa.Column("valid_from", sa.Date, nullable=False),
        sa.Column("valid_until", sa.Date, nullable=False),
        sa.Column("evidence_ref", sa.String(512), nullable=True),
        *_timestamps(),
    )

    # crew_currencies -----------------------------------------------------------
    op.create_table(
        "crew_currencies",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("currency_type", currency_type, nullable=False),
        sa.Column("last_completed_date", sa.Date, nullable=False),
        sa.Column("expires_date", sa.Date, nullable=False),
        sa.Column("evidence_ref", sa.String(512), nullable=True),
        *_timestamps(),
    )

    # sectors -------------------------------------------------------------------
    op.create_table(
        "sectors",
        _uuid_pk(),
        _operator_scope(),
        sa.Column("flight_no", sa.String(16), nullable=False, index=True),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("origin", sa.String(8), nullable=False),
        sa.Column("destination", sa.String(8), nullable=False),
        sa.Column("std", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("atd", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ata", sa.DateTime(timezone=True), nullable=True),
        sa.Column("aircraft_reg", sa.String(16), nullable=False),
        sa.Column("aircraft_type", sa.String(32), nullable=False),
        sa.Column("status", sector_status, nullable=False, server_default="PLANNED"),
        *_timestamps(),
    )

    # sector_assignments --------------------------------------------------------
    op.create_table(
        "sector_assignments",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "sector_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sectors.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="RESTRICT"),
            nullable=False,
            index=True,
        ),
        sa.Column("role_on_sector", sa.String(16), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("sector_id", "crew_id", name="uq_sector_assignment_sector_crew"),
    )

    # flight_duty_periods -------------------------------------------------------
    op.create_table(
        "flight_duty_periods",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("date", sa.Date, nullable=False, index=True),
        sa.Column("report_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("off_duty_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sectors_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("flight_hours", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("duty_hours", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("type", fdp_type, nullable=False, server_default="FDP"),
        sa.Column("legality_state", legality_state, nullable=False, server_default="LEGAL"),
        sa.Column(
            "ftl_rules_applied",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        *_timestamps(),
    )

    # ftl_rules -----------------------------------------------------------------
    op.create_table(
        "ftl_rules",
        _uuid_pk(),
        _operator_scope(),
        sa.Column("rule_id", sa.String(128), nullable=False, index=True),
        sa.Column("description", sa.String(2048), nullable=False),
        sa.Column("regulation_ref", sa.String(256), nullable=False),
        sa.Column("calculation_logic_ref", sa.String(256), nullable=False),
        sa.Column(
            "applies_to",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("source", rule_source, nullable=False, server_default="MANUAL_REVIEW"),
        *_timestamps(),
    )

    # leave_requests ------------------------------------------------------------
    op.create_table(
        "leave_requests",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "crew_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", leave_type, nullable=False),
        sa.Column("date_from", sa.Date, nullable=False),
        sa.Column("date_to", sa.Date, nullable=False),
        sa.Column("status", leave_status, nullable=False, server_default="PENDING"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "approver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )

    # swap_requests -------------------------------------------------------------
    op.create_table(
        "swap_requests",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "crew_id_initiator",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "crew_id_counterparty",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("crew.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("fdp_or_sector_ref", sa.String(128), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", swap_status, nullable=False, server_default="PENDING"),
        sa.Column(
            "approver_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_timestamps(),
    )

    # audit_events --------------------------------------------------------------
    op.create_table(
        "audit_events",
        _uuid_pk(),
        _operator_scope(),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("action", sa.String(128), nullable=False, index=True),
        sa.Column("entity_type", sa.String(64), nullable=False, index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("before_state", postgresql.JSONB, nullable=True),
        sa.Column("after_state", postgresql.JSONB, nullable=True),
        *_timestamps(),
    )

    # audit_events is append-only — block UPDATE / DELETE at the database
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_events_append_only()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only (operation: %)', TG_OP;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_update
        BEFORE UPDATE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_no_delete
        BEFORE DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_append_only();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events")
    op.execute("DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events")
    op.execute("DROP FUNCTION IF EXISTS audit_events_append_only()")

    for tbl in (
        "audit_events",
        "swap_requests",
        "leave_requests",
        "ftl_rules",
        "flight_duty_periods",
        "sector_assignments",
        "sectors",
        "crew_currencies",
        "crew_type_ratings",
        "crew",
        "users",
        "operators",
    ):
        op.drop_table(tbl)

    for enum_name in (
        "swap_status",
        "leave_status",
        "leave_type",
        "rule_source",
        "legality_state",
        "fdp_type",
        "sector_status",
        "currency_type",
        "contract_type",
        "crew_role",
        "user_role",
        "operator_tier",
    ):
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
