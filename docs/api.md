# API surface (v1)

The authoritative API surface is the OpenAPI document at
`http://localhost:8000/openapi.json` (rendered at `/docs`). This file
documents the intended Phase 6 surface from the project plan and how each
endpoint maps to a phase.

All endpoints live under `/api/v1/`. JWT is required everywhere except
`/auth/login`.

| Path                                | Phase | Description                              |
|-------------------------------------|------:|------------------------------------------|
| `POST /auth/login`                  | 3     | Crewing Officer login                    |
| `POST /auth/refresh`                | 3     | Token refresh                            |
| `POST /auth/logout`                 | 3     | Invalidate session                       |
| `GET /crew`                         | 1     | List crew                                |
| `POST /crew`                        | 1     | Create crew                              |
| `GET /crew/{id}`                    | 1     | Get crew                                 |
| `PATCH /crew/{id}`                  | 1     | Update crew                              |
| `GET /crew/{id}/currency`           | 1     | Crew currency status                     |
| `POST /crew/{id}/currency`          | 1     | Record currency                          |
| `GET /roster?from=&to=`             | 2     | Roster slice                             |
| `POST /roster/generate`             | 2     | Async optimisation                       |
| `GET /roster/jobs/{job_id}`         | 2     | Job status                               |
| `POST /roster/publish`              | 3     | Make roster immutable                    |
| `POST /roster/amend`                | 3     | Post-publication amendment               |
| `POST /roster/explain`              | 2     | Binding constraints for an FDP           |
| `POST /ftl/check`                   | 1     | Validate a roster slice                  |
| `POST /ftl/validate-fdp`            | 1     | Single FDP rule trace                    |
| `POST /leave`                       | 3     | Submit leave request                     |
| `GET /leave?status=PENDING`         | 3     | List leave requests                      |
| `PATCH /leave/{id}`                 | 3     | Approve / reject                         |
| `POST /swap`                        | 3     | Submit swap request                      |
| `GET /swap?status=PENDING`          | 3     | List swap requests                      |
| `PATCH /swap/{id}`                  | 3     | Approve / reject                         |
| `POST /audit/generate`              | 5     | Async PDF generation                     |
| `GET /audit/packs?from=&to=`        | 5     | List generated packs                     |
| `GET /audit/packs/{id}/download`    | 5     | Download PDF                             |
| `GET /audit/packs/{id}/verify`      | 5     | Verify hash signature                    |
| `GET /settings/operator`            | 3     | Operator profile                         |
| `PATCH /settings/operator`          | 3     | Update operator profile                  |
| `GET /settings/ftl-rules`           | 3     | List rule overrides                      |
| `PATCH /settings/ftl-rules/{id}`    | 3     | Edit rule override (gated)               |

The Phase 0 backend ships the route groups but every concrete endpoint
returns `501 Not Implemented` until its phase lands.
