"""Reference-data endpoints — the curated aircraft-type menu, etc.

Authenticated but operator-agnostic — every operator sees the same
curated list. Used to source the aircraft-type dropdown in the fleet
registry and the crew type-rating form.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.reference import AircraftTypeOut
from app.services import aircraft_types

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
