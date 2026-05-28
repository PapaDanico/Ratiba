"""Public holiday reference data + endpoint."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app.models.user import User
from app.services import public_holidays as ph


def test_easter_known_dates() -> None:
    # Gregorian Easter Sundays — cross-checked against published tables.
    assert ph._easter(2025) == date(2025, 4, 20)
    assert ph._easter(2026) == date(2026, 4, 5)
    assert ph._easter(2027) == date(2027, 3, 28)


def test_kenya_has_madaraka_and_mashujaa() -> None:
    ke = ph.get_holidays("KE", 2025)
    names = {h.name for h in ke}
    assert "Madaraka Day" in names
    assert "Mashujaa Day" in names
    assert "Jamhuri Day" in names
    # Fixed national days fall on their statutory dates.
    by_name = {h.name: h.date for h in ke}
    assert by_name["Madaraka Day"] == date(2025, 6, 1)
    assert by_name["Mashujaa Day"] == date(2025, 10, 20)


def test_each_country_covered_2025_2030() -> None:
    for country in ph.SUPPORTED_COUNTRIES:
        for year in ph.SUPPORTED_YEARS:
            holidays = ph.get_holidays(country, year)
            assert holidays, f"{country} {year} returned no holidays"
            # Always sorted ascending by date.
            assert holidays == sorted(holidays, key=lambda h: h.date)


def test_unsupported_country_and_year_return_empty() -> None:
    assert ph.get_holidays("ZZ", 2025) == []
    assert ph.get_holidays("KE", 1999) == []


def test_date_range_filters_inclusive() -> None:
    rng = ph.holidays_for_date_range("KE", date(2025, 6, 1), date(2025, 6, 1))
    assert [h.name for h in rng] == ["Madaraka Day"]


def test_date_range_spanning_year_boundary() -> None:
    rng = ph.holidays_for_date_range("KE", date(2025, 12, 20), date(2026, 1, 5))
    names = {h.name for h in rng}
    assert "Christmas Day" in names
    assert "Boxing Day" in names
    assert "New Year's Day" in names


def test_endpoint_returns_kenya_holidays(auth_client: tuple[TestClient, User]) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/reference/public-holidays",
        params={"country_code": "KE", "date_from": "2025-01-01", "date_to": "2025-12-31"},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()
    assert len(rows) >= 10
    sample = rows[0]
    assert {"country_code", "date", "name", "is_variable"} <= set(sample)
    assert all(r["country_code"] == "KE" for r in rows)


def test_endpoint_unsupported_country_returns_empty(
    auth_client: tuple[TestClient, User],
) -> None:
    client, _ = auth_client
    resp = client.get(
        "/api/v1/reference/public-holidays",
        params={"country_code": "ZZ", "date_from": "2025-01-01", "date_to": "2025-12-31"},
    )
    assert resp.status_code == 200
    assert resp.json() == []
