# ADR 0003: Multi-tenancy from day one and append-only audit log

* **Status:** Accepted — 2026-05-27
* **Deciders:** Capt. Dan Ng'ong'a, Claude Code
* **References:** Project Plan v1.0 §4, §5 Phase 1, §5 Phase 5

## Context

The MVP launches with one operator but the commercial thesis depends on
multi-operator delivery within months. Retrofitting tenancy is expensive
and risky; we pay the small cost now to avoid it.

Separately, KCAA-presentable audit packs require a tamper-evident,
reconstructable history of every change touching a roster or a crew
record. The path of least resistance — `UPDATE crew SET ...` with no
record of the prior state — would make Phase 5 impossible.

## Decision

1. **Operator scoping.** Every business table carries `operator_id` from
   day one. A SQLAlchemy mixin (`OperatorScopedMixin`) enforces this in
   models; Phase 1 will add a row-level security policy as belt-and-braces.
2. **Append-only audit.** `audit_events` is guarded by a PostgreSQL
   trigger that raises on `UPDATE` or `DELETE`. The only legal writer is
   `app.services.audit_log.record()`. Phase 1 onwards: every endpoint that
   writes a business row also writes an audit event in the same
   transaction.

## Consequences

- Adding operator #2 is a data-import exercise, not a schema migration.
- Audit packs can reconstruct the full history of any roster slice with
  one SQL query.
- Tests must seed an `Operator` row and pass `operator_id` through every
  fixture; conftest helpers will minimise the boilerplate.
