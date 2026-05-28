"""CSV importer endpoints — Phase 6 onboarding."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from app.models.user import User

CREW_CSV = b"""employee_no,first_name,last_name,role,date_of_hire,date_of_birth,base_station,contract_type,languages,faith_observance_flags
IF001,Amani,Otieno,CAPT,2018-06-01,1980-02-12,HKJK,FULL_TIME,en;sw,sunday_protected=true
IF002,Peter,Onyango,FO,2022-01-15,1993-11-04,HKJK,FULL_TIME,en,
"""

CURRENCIES_CSV = b"""employee_no,currency_type,last_completed_date,expires_date,evidence_ref
IF001,OPC,2026-01-10,2026-12-01,OPC-2026-001
IF002,LPC,2026-02-15,2026-08-15,
"""

TYPE_RATINGS_CSV = b"""employee_no,aircraft_type,valid_from,valid_until,evidence_ref
IF001,DH8D,2020-01-01,2028-01-01,TR-DH8D-001
IF002,DH8D,2022-06-01,2027-06-01,
"""

FDPS_CSV = b"""employee_no,date,report_time,off_duty_time,sectors_count,flight_hours,duty_hours
IF001,2026-04-01,2026-04-01T05:00:00+00:00,2026-04-01T13:00:00+00:00,2,6.0,8.0
"""


def _upload(client: TestClient, path: str, content: bytes, *, commit: bool = True) -> dict:
    resp = client.post(
        f"/api/v1/onboarding/{path}?commit={'true' if commit else 'false'}",
        files={"file": ("file.csv", io.BytesIO(content), "text/csv")},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_crew_import_inserts_rows(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    body = _upload(client, "crew", CREW_CSV)
    assert body["inserted"] == 2
    assert body["errors"] == []

    rows = client.get("/api/v1/crew").json()
    assert {r["employee_no"] for r in rows} == {"IF001", "IF002"}
    if001 = next(r for r in rows if r["employee_no"] == "IF001")
    assert if001["faith_observance_flags"] == {"sunday_protected": True}
    assert if001["languages"] == ["en", "sw"]


def test_crew_import_idempotent_on_employee_no(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    _upload(client, "crew", CREW_CSV)
    # Re-uploading the same CSV updates, doesn't duplicate.
    body = _upload(client, "crew", CREW_CSV)
    assert body["inserted"] == 0
    assert body["updated"] == 2
    rows = client.get("/api/v1/crew").json()
    assert len(rows) == 2


def test_crew_import_dry_run_does_not_persist(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    body = _upload(client, "crew", CREW_CSV, commit=False)
    assert body["inserted"] == 2
    rows = client.get("/api/v1/crew").json()
    assert rows == []


def test_currencies_and_type_ratings_chain(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    _upload(client, "crew", CREW_CSV)
    body = _upload(client, "type-ratings", TYPE_RATINGS_CSV)
    assert body["inserted"] == 2
    body = _upload(client, "currencies", CURRENCIES_CSV)
    assert body["inserted"] == 2


def test_historical_fdps_seeds_cumulative_history(
    auth_client: tuple[TestClient, User], db_session
) -> None:
    client, _ = auth_client
    _upload(client, "crew", CREW_CSV)
    _upload(client, "historical-fdps", FDPS_CSV)

    from app.models import FlightDutyPeriod

    db_session.expire_all()
    fdps = db_session.query(FlightDutyPeriod).all()
    assert len(fdps) == 1
    assert "IMPORTED-HISTORICAL" in fdps[0].ftl_rules_applied


def test_missing_required_column_returns_400(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    bad = b"employee_no,first_name\nIF001,Amani\n"
    resp = client.post(
        "/api/v1/onboarding/crew",
        files={"file": ("file.csv", io.BytesIO(bad), "text/csv")},
    )
    assert resp.status_code == 400
    assert "missing required columns" in resp.json()["detail"]


def test_row_error_reports_row_number(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    bad = (
        b"employee_no,first_name,last_name,role,date_of_hire,date_of_birth,"
        b"base_station,contract_type\n"
        b"IF001,Amani,Otieno,CAPT,not-a-date,1980-02-12,HKJK,FULL_TIME\n"
    )
    body = _upload(client, "crew", bad)
    assert body["inserted"] == 0
    assert len(body["errors"]) == 1
    assert body["errors"][0]["row"] == 2


def test_type_rating_for_unknown_crew_errors(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    body = _upload(client, "type-ratings", TYPE_RATINGS_CSV)
    assert body["inserted"] == 0
    assert any("not found" in e["message"] for e in body["errors"])


def test_oversized_upload_rejected_413(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    huge = b"x" * (5 * 1024 * 1024 + 1)  # 1 byte over the 5 MB cap
    resp = client.post(
        "/api/v1/onboarding/crew",
        files={"file": ("big.csv", io.BytesIO(huge), "text/csv")},
    )
    assert resp.status_code == 413, resp.text


def test_too_many_rows_rejected_400(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    header = (
        b"employee_no,first_name,last_name,role,date_of_hire,date_of_birth,"
        b"base_station,contract_type\n"
    )
    row = b"IF%05d,A,B,CAPT,2020-01-01,1980-01-01,HKJK,FULL_TIME\n"
    body = header + b"".join(row % i for i in range(20_001))
    resp = client.post(
        "/api/v1/onboarding/crew",
        files={"file": ("many.csv", io.BytesIO(body), "text/csv")},
    )
    assert resp.status_code == 400, resp.text
    assert "row limit" in resp.json()["detail"]


def test_binary_upload_rejected_400(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    binary = bytes(range(256)) * 16  # non-UTF-8 bytes
    resp = client.post(
        "/api/v1/onboarding/crew",
        files={"file": ("image.csv", io.BytesIO(binary), "text/csv")},
    )
    assert resp.status_code == 400, resp.text
    assert "UTF-8" in resp.json()["detail"]
