"""Read-only 'limits in force' endpoint."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.models.constraint import (
    ConstraintReviewStatus,
    ConstraintRule,
    ConstraintSet,
    ConstraintSetStatus,
)


def test_limits_default_to_generic_baseline(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get("/api/v1/ftl/limits")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["source"] == "baseline"
    assert "CAA-AC-OPS033" in body["regulation_ref"]
    assert body["limits"]["fdp_max_basic_by_band"]["DAY_PEAK"] == 13.0
    assert body["limits"]["fdp_scheduled_ceiling_basic_h"] == 14.0


def test_limits_reflect_accepted_operator_scheme(
    auth_client: tuple[TestClient, User], db_session: Session
) -> None:
    client, user = auth_client
    cset = ConstraintSet(
        operator_id=user.operator_id,
        om_a_revision="OM-A rev 4",
        status=ConstraintSetStatus.ACCEPTED,
        rule_count=1,
        accepted_at=datetime.now(UTC),
    )
    db_session.add(cset)
    db_session.flush()
    db_session.add(
        ConstraintRule(
            constraint_set_id=cset.id,
            rule_key="cumul_duty_7d_h",
            final_value=55.0,
            review_status=ConstraintReviewStatus.EDITED,
        )
    )
    db_session.commit()

    body = client.get("/api/v1/ftl/limits").json()
    assert body["source"] == "operator"
    assert body["limits"]["cumul_duty_7d_h"] == 55.0  # overridden from 60
