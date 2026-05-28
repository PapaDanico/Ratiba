"""Reference-data schemas (aircraft types, etc.)."""

from __future__ import annotations

from pydantic import BaseModel


class AircraftTypeOut(BaseModel):
    icao: str
    manufacturer: str
    model: str
    category: str
    typical_seats: int
    label: str  # "DH8D — De Havilland Canada Dash 8 Q400" for dropdown display
