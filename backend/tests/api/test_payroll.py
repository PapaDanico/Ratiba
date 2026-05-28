"""Payroll / duty-hours CSV export."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import LeaveRequest, User
from app.models.leave import LeaveStatus, LeaveType


def _create_crew(client: TestClient, *, employee_no: str, role: str = "CAPT") -> dict:
    return client.post(
        "/api/v1/crew",
        json={
            "employee_no": employee_no,
            "first_name": "Pay",
            "last_name": "Roller",
            "role": role,
            "date_of_hire": "2020-01-01",
            "date_of_birth": "1985-01-01",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()


def test_payroll_csv_headers_and_row(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    _create_crew(client, employee_no="P1")

    resp = client.get(
        "/api/v1/reports/payroll.csv",
        params={"date_from": "2025-06-01", "date_to": "2025-06-30"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    reader = csv.DictReader(io.StringIO(resp.text))
    assert reader.fieldnames == [
        "employee_no",
        "name",
        "role",
        "base",
        "fdp_count",
        "duty_hours",
        "block_hours",
        "standby_days",
        "leave_days",
        "sick_days",
    ]
    rows = list(reader)
    p1 = next(r for r in rows if r["employee_no"] == "P1")
    assert p1["name"] == "Pay Roller"
    assert p1["fdp_count"] == "0"  # nothing published yet
    assert p1["duty_hours"] == "0.0"


def test_payroll_counts_approved_leave(
    auth_client: tuple[TestClient, User],
    db_session: Session,
) -> None:
    client, user = auth_client
    crew = _create_crew(client, employee_no="P2")
    # Insert 3 days of approved annual leave (10–12 inclusive) within the period.
    db_session.add(
        LeaveRequest(
            operator_id=user.operator_id,
            crew_id=uuid.UUID(crew["id"]),
            type=LeaveType.ANNUAL,
            date_from=date(2025, 6, 10),
            date_to=date(2025, 6, 12),
            status=LeaveStatus.APPROVED,
        )
    )
    db_session.commit()

    resp = client.get(
        "/api/v1/reports/payroll.csv",
        params={"date_from": "2025-06-01", "date_to": "2025-06-30"},
    )
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    p2 = next(r for r in rows if r["employee_no"] == "P2")
    assert p2["leave_days"] == "3"


def test_payroll_rejects_reversed_range(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/reports/payroll.csv",
        params={"date_from": "2025-06-30", "date_to": "2025-06-01"},
    )
    assert resp.status_code == 422
