"""Reference-data endpoints — curated aircraft-type menu and public holidays.

Authenticated but operator-agnostic — every operator sees the same
curated list. Used to source the aircraft-type dropdown in the fleet
registry and the crew type-rating form.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.reference import AircraftTypeOut
from app.services import aircraft_types
from app.services.public_holidays import (
    SUPPORTED_COUNTRIES,
    holidays_for_date_range,
)

router = APIRouter()


@router.get("/aircraft-types", response_model=list[AircraftTypeOut])
def list_aircraft_types(
    _user: User = Depends(get_current_user),
) -> list[AircraftTypeOut]:
    return [
        AircraftTypeOut(
            icao=t.icao,
            manufacturer=t.manufacturer,
            model=t.model,
            category=t.category,
            typical_seats=t.typical_seats,
            label=f"{t.icao} — {t.manufacturer} {t.model}",
        )
        for t in aircraft_types.all_types()
    ]


class PublicHolidayOut(BaseModel):
    country_code: str
    date: date
    name: str
    is_variable: bool


@router.get(
    "/public-holidays",
    response_model=list[PublicHolidayOut],
    summary="Public holidays for a country within a date range",
)
def list_public_holidays(
    country_code: str = Query(..., description="ISO 3166-1 alpha-2 (KE, UG, TZ, ET)"),
    date_from: date = Query(...),
    date_to: date = Query(...),
    _user: User = Depends(get_current_user),
) -> list[PublicHolidayOut]:
    country = country_code.upper()
    if country not in SUPPORTED_COUNTRIES:
        return []
    holidays = holidays_for_date_range(country, date_from, date_to)
    return [
        PublicHolidayOut(
            country_code=h.country_code,
            date=h.date,
            name=h.name,
            is_variable=h.is_variable,
        )
        for h in holidays
    ]
