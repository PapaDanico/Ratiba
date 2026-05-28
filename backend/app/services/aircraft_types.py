"""Curated aircraft-type reference for sub-scale East/Central African operators.

The list is intentionally scoped to the types actually flown by the
3–10 aircraft segment Ratiba targets — regional turboprops, light
utility twins/singles, and the smaller regional jets — rather than a
full ICAO type-designator dump. It's the source for the aircraft-type
dropdown in the fleet registry and crew type-rating entry.

Each entry uses the ICAO type designator as the stable key (what crew
type ratings and OM-A FTL chapters reference). Operators that fly
something not on this list can still type a free-form designator; the
list is the curated default, not a hard whitelist.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AircraftType:
    icao: str  # ICAO type designator — the stable key
    manufacturer: str
    model: str
    category: str  # turboprop | regional_jet | light | narrowbody
    typical_seats: int


# Ordered by category then by how common they are in the EAC sub-scale segment.
AIRCRAFT_TYPES: tuple[AircraftType, ...] = (
    # --- Regional turboprops (the workhorses of EAC sub-scale ops) ---
    AircraftType("DH8D", "De Havilland Canada", "Dash 8 Q400", "turboprop", 78),
    AircraftType("DH8C", "De Havilland Canada", "Dash 8-300", "turboprop", 50),
    AircraftType("DH8B", "De Havilland Canada", "Dash 8-200", "turboprop", 37),
    AircraftType("DH8A", "De Havilland Canada", "Dash 8-100", "turboprop", 37),
    AircraftType("AT76", "ATR", "ATR 72-600", "turboprop", 70),
    AircraftType("AT75", "ATR", "ATR 72-500", "turboprop", 70),
    AircraftType("AT72", "ATR", "ATR 72-200", "turboprop", 66),
    AircraftType("AT46", "ATR", "ATR 42-600", "turboprop", 48),
    AircraftType("AT45", "ATR", "ATR 42-500", "turboprop", 48),
    AircraftType("AT43", "ATR", "ATR 42-300", "turboprop", 48),
    AircraftType("B190", "Beechcraft", "1900D", "turboprop", 19),
    AircraftType("F50", "Fokker", "50", "turboprop", 56),
    AircraftType("SF34", "Saab", "340", "turboprop", 34),
    AircraftType("JS41", "BAe", "Jetstream 41", "turboprop", 29),
    AircraftType("D228", "Dornier", "228", "turboprop", 19),
    AircraftType("L410", "Let", "L-410 Turbolet", "turboprop", 19),
    # --- Light utility (bush + feeder ops, common in Kenya/Tanzania) ---
    AircraftType("C208", "Cessna", "208 Caravan", "light", 12),
    AircraftType("C208B", "Cessna", "208B Grand Caravan", "light", 14),
    AircraftType("DHC6", "De Havilland Canada", "DHC-6 Twin Otter", "light", 19),
    AircraftType("PC12", "Pilatus", "PC-12", "light", 9),
    AircraftType("C404", "Cessna", "404 Titan", "light", 10),
    AircraftType("C402", "Cessna", "402", "light", 9),
    AircraftType("BN2P", "Britten-Norman", "BN-2 Islander", "light", 9),
    # --- Regional jets ---
    AircraftType("E145", "Embraer", "ERJ 145", "regional_jet", 50),
    AircraftType("E170", "Embraer", "E170", "regional_jet", 76),
    AircraftType("E190", "Embraer", "E190", "regional_jet", 100),
    AircraftType("CRJ2", "Bombardier", "CRJ200", "regional_jet", 50),
    AircraftType("CRJ9", "Bombardier", "CRJ900", "regional_jet", 90),
    AircraftType("F100", "Fokker", "100", "regional_jet", 100),
    AircraftType("F70", "Fokker", "70", "regional_jet", 79),
    AircraftType("F28", "Fokker", "F28 Fellowship", "regional_jet", 65),
    # --- Narrowbody (top of the sub-scale range / charter) ---
    AircraftType("B733", "Boeing", "737-300", "narrowbody", 140),
    AircraftType("B738", "Boeing", "737-800", "narrowbody", 162),
    AircraftType("B737", "Boeing", "737-700", "narrowbody", 130),
    AircraftType("B732", "Boeing", "737-200", "narrowbody", 120),
    AircraftType("A319", "Airbus", "A319", "narrowbody", 128),
    AircraftType("A320", "Airbus", "A320", "narrowbody", 150),
    AircraftType("A321", "Airbus", "A321", "narrowbody", 180),
)

_BY_ICAO = {t.icao: t for t in AIRCRAFT_TYPES}


def all_types() -> tuple[AircraftType, ...]:
    return AIRCRAFT_TYPES


def is_known(icao: str) -> bool:
    return icao.strip().upper() in _BY_ICAO


def get(icao: str) -> AircraftType | None:
    return _BY_ICAO.get(icao.strip().upper())
