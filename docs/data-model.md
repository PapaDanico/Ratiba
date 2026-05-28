# Data model

Living reference. Authoritative form is `backend/app/models/` and the
`alembic/versions/` migration; this file documents intent.

All tables include `id` (UUID), `created_at`, `updated_at`,
`created_by_user_id`. Every business table also carries `operator_id` for
multi-tenancy from day one. Writes are journalled to `audit_events`, which
is append-only (enforced via PostgreSQL triggers in migration `0001`).

## Entity reference

See Section 4 of `Ratiba_Project_Plan_v1.md` for the full schema. The
following table maps each entity to its ORM module:

| Entity                | Module                                    |
|-----------------------|-------------------------------------------|
| `operators`           | `app/models/operator.py`                  |
| `users`               | `app/models/user.py`                      |
| `crew`                | `app/models/crew.py`                      |
| `crew_type_ratings`   | `app/models/training.py`                  |
| `crew_currencies`     | `app/models/training.py`                  |
| `sectors`             | `app/models/roster.py`                    |
| `sector_assignments`  | `app/models/roster.py`                    |
| `flight_duty_periods` | `app/models/ftl.py`                       |
| `ftl_rules`           | `app/models/ftl.py`                       |
| `leave_requests`      | `app/models/leave.py`                     |
| `swap_requests`       | `app/models/swap.py`                      |
| `audit_events`        | `app/models/audit.py` *(append-only)*     |

## Append-only audit

The `audit_events` table is guarded by a PostgreSQL trigger that raises on
any `UPDATE` or `DELETE`. The only legal writer is
`app.services.audit_log.record()`.

## Multi-tenancy

Every business query must be scoped by `operator_id`. A Phase 1 review will
add a row-level security policy as belt-and-braces over application-layer
scoping.
