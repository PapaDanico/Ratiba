"""Public holiday data for East/Central African operating countries.

Covers Kenya (KE), Uganda (UG), Tanzania (TZ), and Ethiopia (ET) for
2025–2030. Fixed holidays are exact; Islamic holidays are approximate
(East Africa observance typically matches Saudi Arabia ±1 day).

Used by:
 - /api/v1/reference/public-holidays   (roster calendar shading)
 - FTL soft-constraint layer           (future: flag crew on home-country holiday)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class PublicHoliday:
    country_code: str  # ISO 3166-1 alpha-2
    date: date
    name: str
    is_variable: bool = False  # True for Islamic/Easter-derived dates


# ---------------------------------------------------------------------------
# Easter calculation (Gregorian Computus)
# ---------------------------------------------------------------------------

def _easter(year: int) -> date:
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    month, day = divmod(114 + h + ll - 7 * m, 31)
    return date(year, month, day + 1)


def _good_friday(year: int) -> date:
    return _easter(year) - timedelta(days=2)


def _easter_monday(year: int) -> date:
    return _easter(year) + timedelta(days=1)


# ---------------------------------------------------------------------------
# Islamic holiday approximate dates (East Africa observance)
# Eid al-Fitr = end of Ramadan (1 Shawwal)
# Eid al-Adha = Feast of Sacrifice (10 Dhul-Hijja)
# Maulid      = Prophet's birthday (12 Rabi al-Awwal)
# ---------------------------------------------------------------------------

_EID_AL_FITR: dict[int, date] = {
    2025: date(2025, 3, 30),
    2026: date(2026, 3, 20),
    2027: date(2027, 3, 9),
    2028: date(2028, 2, 26),
    2029: date(2029, 2, 14),
    2030: date(2030, 2, 3),
}

_EID_AL_ADHA: dict[int, date] = {
    2025: date(2025, 6, 6),
    2026: date(2026, 5, 27),
    2027: date(2027, 5, 17),
    2028: date(2028, 5, 5),
    2029: date(2029, 4, 24),
    2030: date(2030, 4, 13),
}

_MAULID: dict[int, date] = {
    2025: date(2025, 9, 4),
    2026: date(2026, 8, 25),
    2027: date(2027, 8, 14),
    2028: date(2028, 8, 2),
    2029: date(2029, 7, 23),
    2030: date(2030, 7, 12),
}


# ---------------------------------------------------------------------------
# Holiday builders per country
# ---------------------------------------------------------------------------

def _kenya_holidays(year: int) -> list[PublicHoliday]:
    ke = "KE"
    h = [
        PublicHoliday(ke, date(year, 1, 1),  "New Year's Day"),
        PublicHoliday(ke, _good_friday(year), "Good Friday",    is_variable=True),
        PublicHoliday(ke, _easter_monday(year), "Easter Monday", is_variable=True),
        PublicHoliday(ke, date(year, 5, 1),  "Labour Day"),
        PublicHoliday(ke, date(year, 6, 1),  "Madaraka Day"),
        PublicHoliday(ke, date(year, 10, 10), "Huduma Day"),
        PublicHoliday(ke, date(year, 10, 20), "Mashujaa Day"),
        PublicHoliday(ke, date(year, 12, 12), "Jamhuri Day"),
        PublicHoliday(ke, date(year, 12, 25), "Christmas Day"),
        PublicHoliday(ke, date(year, 12, 26), "Boxing Day"),
    ]
    if year in _EID_AL_FITR:
        h.append(PublicHoliday(ke, _EID_AL_FITR[year], "Idd ul-Fitr", is_variable=True))
    if year in _EID_AL_ADHA:
        h.append(PublicHoliday(ke, _EID_AL_ADHA[year], "Idd ul-Adha", is_variable=True))
    if year in _MAULID:
        h.append(PublicHoliday(ke, _MAULID[year], "Maulid Day", is_variable=True))
    return h


def _uganda_holidays(year: int) -> list[PublicHoliday]:
    ug = "UG"
    h = [
        PublicHoliday(ug, date(year, 1, 1),  "New Year's Day"),
        PublicHoliday(ug, date(year, 1, 26), "Liberation Day"),
        PublicHoliday(ug, date(year, 2, 16), "Archbishop Janani Luwum Day"),
        PublicHoliday(ug, date(year, 3, 8),  "International Women's Day"),
        PublicHoliday(ug, _good_friday(year), "Good Friday",    is_variable=True),
        PublicHoliday(ug, _easter_monday(year), "Easter Monday", is_variable=True),
        PublicHoliday(ug, date(year, 5, 1),  "Labour Day"),
        PublicHoliday(ug, date(year, 6, 3),  "Martyrs Day"),
        PublicHoliday(ug, date(year, 6, 9),  "Heroes Day"),
        PublicHoliday(ug, date(year, 10, 9), "Independence Day"),
        PublicHoliday(ug, date(year, 12, 25), "Christmas Day"),
        PublicHoliday(ug, date(year, 12, 26), "Boxing Day"),
    ]
    if year in _EID_AL_FITR:
        h.append(PublicHoliday(ug, _EID_AL_FITR[year], "Eid al-Fitr", is_variable=True))
    if year in _EID_AL_ADHA:
        h.append(PublicHoliday(ug, _EID_AL_ADHA[year], "Eid al-Adha", is_variable=True))
    return h


def _tanzania_holidays(year: int) -> list[PublicHoliday]:
    tz = "TZ"
    h = [
        PublicHoliday(tz, date(year, 1, 1),  "New Year's Day"),
        PublicHoliday(tz, date(year, 1, 12), "Zanzibar Revolution Day"),
        PublicHoliday(tz, _good_friday(year), "Good Friday",    is_variable=True),
        PublicHoliday(tz, _easter_monday(year), "Easter Monday", is_variable=True),
        PublicHoliday(tz, date(year, 4, 7),  "Karume Day"),
        PublicHoliday(tz, date(year, 4, 26), "Union Day"),
        PublicHoliday(tz, date(year, 5, 1),  "Workers Day"),
        PublicHoliday(tz, date(year, 7, 7),  "Saba Saba Day"),
        PublicHoliday(tz, date(year, 8, 8),  "Nane Nane Day"),
        PublicHoliday(tz, date(year, 10, 14), "Nyerere Day"),
        PublicHoliday(tz, date(year, 12, 9),  "Independence Day"),
        PublicHoliday(tz, date(year, 12, 25), "Christmas Day"),
        PublicHoliday(tz, date(year, 12, 26), "Boxing Day"),
    ]
    if year in _EID_AL_FITR:
        h.append(PublicHoliday(tz, _EID_AL_FITR[year], "Eid al-Fitr", is_variable=True))
    if year in _EID_AL_ADHA:
        h.append(PublicHoliday(tz, _EID_AL_ADHA[year], "Eid al-Adha", is_variable=True))
    if year in _MAULID:
        h.append(PublicHoliday(tz, _MAULID[year], "Maulid Day", is_variable=True))
    return h


def _ethiopia_holidays(year: int) -> list[PublicHoliday]:
    """Ethiopian public holidays. Note: Ethiopia uses the Ge'ez calendar
    internally, but these dates are in the Gregorian equivalent for
    compatibility with the rest of the system. Fasika (Ethiopian Easter)
    follows the Coptic/Julian Easter calculation (13 days after Gregorian
    Easter in most years); we use a lookup table for precision."""
    et = "ET"
    # Ethiopian Fasika (Orthodox Easter) — approximate Gregorian equivalent
    _fasika: dict[int, date] = {
        2025: date(2025, 4, 20),   # same as Gregorian in 2025
        2026: date(2026, 4, 19),
        2027: date(2027, 4, 11),
        2028: date(2028, 4, 30),
        2029: date(2029, 4, 15),
        2030: date(2030, 4, 28),
    }
    h = [
        PublicHoliday(et, date(year, 1, 7),  "Genna (Ethiopian Christmas)"),
        PublicHoliday(et, date(year, 1, 19), "Timkat (Ethiopian Epiphany)"),
        PublicHoliday(et, date(year, 3, 2),  "Victory of Adwa"),
        PublicHoliday(et, date(year, 5, 1),  "International Workers Day"),
        PublicHoliday(et, date(year, 5, 5),  "Patriots Victory Day"),
        PublicHoliday(et, date(year, 5, 28), "Downfall of the Derg"),
        PublicHoliday(et, date(year, 9, 11), "Ethiopian New Year (Enkutatash)"),
        PublicHoliday(et, date(year, 9, 27), "Meskel (Finding of the True Cross)"),
    ]
    if year in _fasika:
        h.append(PublicHoliday(et, _fasika[year], "Fasika (Ethiopian Easter)", is_variable=True))
    if year in _EID_AL_FITR:
        h.append(PublicHoliday(et, _EID_AL_FITR[year], "Eid al-Fitr", is_variable=True))
    if year in _EID_AL_ADHA:
        h.append(PublicHoliday(et, _EID_AL_ADHA[year], "Eid al-Adha", is_variable=True))
    if year in _MAULID:
        h.append(PublicHoliday(et, _MAULID[year], "Mouloud", is_variable=True))
    return h


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_BUILDERS = {
    "KE": _kenya_holidays,
    "UG": _uganda_holidays,
    "TZ": _tanzania_holidays,
    "ET": _ethiopia_holidays,
}

SUPPORTED_COUNTRIES = tuple(_BUILDERS.keys())
SUPPORTED_YEARS = range(2025, 2031)


def get_holidays(country_code: str, year: int) -> list[PublicHoliday]:
    """Return sorted public holidays for the given country/year.

    Returns an empty list for unsupported country codes or years
    rather than raising, so callers can safely render without a holiday
    layer when the country is outside the supported set.
    """
    builder = _BUILDERS.get(country_code.upper())
    if builder is None or year not in SUPPORTED_YEARS:
        return []
    return sorted(builder(year), key=lambda h: h.date)


def holidays_for_date_range(
    country_code: str,
    date_from: date,
    date_to: date,
) -> list[PublicHoliday]:
    """All public holidays in [date_from, date_to] for the given country."""
    years = range(date_from.year, date_to.year + 1)
    result: list[PublicHoliday] = []
    for year in years:
        for h in get_holidays(country_code, year):
            if date_from <= h.date <= date_to:
                result.append(h)
    return sorted(result, key=lambda h: h.date)
