"""Run the recurrency expiry digest for every operator.

Invoked on a schedule (Render cron → digest-cron.sh). Runs the digest task
in-process for each operator — no HTTP/auth/queue needed, since this is itself
the scheduled batch job. Usage:

    python scripts/run_digests.py [within_days]   # default 30
"""

from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Operator
from app.tasks.notifications import notify_expiry_digest


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    within_days = int(args[0]) if args else 30
    with SessionLocal() as session:
        operator_ids = [str(o.id) for o in session.scalars(select(Operator)).all()]

    items = 0
    for operator_id in operator_ids:
        result = notify_expiry_digest({"operator_id": operator_id, "within_days": within_days})
        items += int(result.get("items", 0))

    print(f"recurrency digest: {len(operator_ids)} operators, {items} item(s) flagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
