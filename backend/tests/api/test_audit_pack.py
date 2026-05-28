"""KCAA audit pack generation, listing, verification, and download."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.user import User


@pytest.fixture(autouse=True)
def audit_pack_dir(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    """Send pack PDFs to a temp dir per test so they don't accumulate."""
    monkeypatch.setenv("AUDIT_PACK_DIR", str(tmp_path / "audit_packs"))
    get_settings.cache_clear()  # type: ignore[attr-defined]
    yield
    get_settings.cache_clear()  # type: ignore[attr-defined]


def _seed_one_published_day(client: TestClient) -> date:
    """Create two crew + publish a one-day roster so the pack has data."""
    cap = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "PACK-CAP",
            "first_name": "Audit",
            "last_name": "Captain",
            "role": "CAPT",
            "date_of_hire": "2018-06-01",
            "date_of_birth": "1980-02-12",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    fo = client.post(
        "/api/v1/crew",
        json={
            "employee_no": "PACK-FO",
            "first_name": "Audit",
            "last_name": "First Officer",
            "role": "FO",
            "date_of_hire": "2022-01-15",
            "date_of_birth": "1993-11-04",
            "base_station": "HKJK",
            "contract_type": "FULL_TIME",
        },
    ).json()
    day = date(2026, 7, 1)
    std = datetime(2026, 7, 1, 6, 0, tzinfo=UTC)
    client.post(
        "/api/v1/roster/publish",
        json={
            "horizon_from": day.isoformat(),
            "horizon_to": day.isoformat(),
            "sectors": [
                {
                    "sector_id": "PACK-RB-1",
                    "date_local": day.isoformat(),
                    "std": std.isoformat(),
                    "sta": (std + timedelta(hours=3)).isoformat(),
                    "aircraft_reg": "5Y-PACK",
                    "aircraft_type": "DH8D",
                    "block_hours": "3.0",
                }
            ],
            "assignments": [
                {
                    "duty_day_key": f"5Y-PACK|{day.isoformat()}",
                    "date_local": day.isoformat(),
                    "aircraft_reg": "5Y-PACK",
                    "aircraft_type": "DH8D",
                    "sector_ids": ["PACK-RB-1"],
                    "captain_id": cap["employee_no"],
                    "fo_id": fo["employee_no"],
                }
            ],
        },
    ).raise_for_status()
    return day


def test_generate_pack_returns_metadata(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    day = _seed_one_published_day(client)

    resp = client.post(
        "/api/v1/audit/generate",
        json={"period_from": day.isoformat(), "period_to": day.isoformat()},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["fdp_count"] == 2
    assert body["anomaly_count"] == 0
    assert len(body["sha256_hex"]) == 64
    assert body["byte_size"] > 1000  # a real PDF is at least this big


def test_listing_packs_after_generation(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    day = _seed_one_published_day(client)
    client.post(
        "/api/v1/audit/generate",
        json={"period_from": day.isoformat(), "period_to": day.isoformat()},
    ).raise_for_status()

    resp = client.get("/api/v1/audit/packs")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1


def test_verify_returns_matching_hash(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    day = _seed_one_published_day(client)
    created = client.post(
        "/api/v1/audit/generate",
        json={"period_from": day.isoformat(), "period_to": day.isoformat()},
    ).json()

    resp = client.get(f"/api/v1/audit/packs/{created['id']}/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert body["expected_sha256"] == created["sha256_hex"]
    assert body["actual_sha256"] == created["sha256_hex"]


def test_verify_detects_tampering(auth_client: tuple[TestClient, User], db_session) -> None:
    client, _ = auth_client
    day = _seed_one_published_day(client)
    created = client.post(
        "/api/v1/audit/generate",
        json={"period_from": day.isoformat(), "period_to": day.isoformat()},
    ).json()

    # Mutate the bytes on disk.
    from app.models import AuditPack

    db_session.expire_all()
    pack = db_session.get(AuditPack, created["id"])
    assert pack is not None
    with open(pack.storage_path, "ab") as fh:
        fh.write(b"TAMPERED")

    resp = client.get(f"/api/v1/audit/packs/{created['id']}/verify")
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is False
    assert body["actual_sha256"] != body["expected_sha256"]


def test_download_returns_pdf_with_hash_header(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    day = _seed_one_published_day(client)
    created = client.post(
        "/api/v1/audit/generate",
        json={"period_from": day.isoformat(), "period_to": day.isoformat()},
    ).json()

    resp = client.get(f"/api/v1/audit/packs/{created['id']}/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.headers["X-Audit-Pack-SHA256"] == created["sha256_hex"]
    assert resp.content.startswith(b"%PDF")
    assert "filename=" in resp.headers["content-disposition"]


def test_generate_rejects_inverted_period(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    resp = client.post(
        "/api/v1/audit/generate",
        json={"period_from": "2026-07-10", "period_to": "2026-07-01"},
    )
    assert resp.status_code == 422
