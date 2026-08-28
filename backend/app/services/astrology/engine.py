"""
Ephemeris calculation engine.

Wraps the Swiss Ephemeris library (pyswisseph) to compute real
planetary positions, ascendant/house cusps, and derived Vedic
placements (nakshatra/pada) for a given moment and location.

No planetary position is ever hardcoded here — everything is derived
from `swisseph`'s astronomical calculations for the exact julian day
supplied. pyswisseph ships with a built-in Moshier analytical
ephemeris, so it produces accurate results (arc-second level for
planets) without requiring separately-downloaded JPL data files,
which keeps this usable in offline/sandboxed environments.
"""

import datetime
from typing import Dict, Any, List

import swisseph as swe

from backend.app.services.astrology.constants import (
    ZODIAC_SIGNS,
    SIGN_ELEMENT,
    SIGN_MODALITY,
    NAKSHATRAS,
    NAKSHATRA_SPAN_DEG,
    NAKSHATRA_PADA_SPAN_DEG,
    MAJOR_ASPECTS,
)

# Ensure a deterministic ephemeris path (empty string -> use built-in
# Moshier fallback when no external .se1 data files are installed).
swe.set_ephe_path("")

PLANET_IDS = {
    "Sun": swe.SUN,
    "Moon": swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus": swe.VENUS,
    "Mars": swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn": swe.SATURN,
    "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE,
    "Pluto": swe.PLUTO,
    "Rahu": swe.MEAN_NODE,  # Mean lunar north node
}

WESTERN_PLANETS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter",
    "Saturn", "Uranus", "Neptune", "Pluto",
]

VEDIC_PLANETS = [
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu",
]


def _sign_of(longitude: float):
    longitude = longitude % 360.0
    idx = int(longitude // 30) % 12
    return ZODIAC_SIGNS[idx], round(longitude - idx * 30, 2)


def to_julian_day_ut(birth_date: datetime.date, birth_time: datetime.time, tz_offset_hours: float) -> float:
    """Converts local civil birth date/time + UTC offset into a Julian Day (Universal Time)."""
    local_hour = birth_time.hour + birth_time.minute / 60.0 + birth_time.second / 3600.0
    ut_hour = local_hour - float(tz_offset_hours)
    return swe.julday(birth_date.year, birth_date.month, birth_date.day, ut_hour)


def compute_planets(jd_ut: float, sidereal: bool) -> Dict[str, Dict[str, Any]]:
    """Computes planetary longitudes/signs/retrograde status for the given Julian Day."""
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    if sidereal:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        flags |= swe.FLG_SIDEREAL

    results: Dict[str, Dict[str, Any]] = {}
    for name, pid in PLANET_IDS.items():
        pos, _ret_flags = swe.calc_ut(jd_ut, pid, flags)
        lon, _lat, _dist, speed = pos[0], pos[1], pos[2], pos[3]
        sign, deg_in_sign = _sign_of(lon)
        results[name] = {
            "longitude": round(lon % 360.0, 4),
            "sign": sign,
            "degree_in_sign": deg_in_sign,
            "retrograde": speed < 0,
        }

    # Ketu (south node) is always exactly opposite Rahu.
    rahu_lon = results["Rahu"]["longitude"]
    ketu_lon = (rahu_lon + 180.0) % 360.0
    ketu_sign, ketu_deg = _sign_of(ketu_lon)
    results["Ketu"] = {
        "longitude": round(ketu_lon, 4),
        "sign": ketu_sign,
        "degree_in_sign": ketu_deg,
        "retrograde": True,
    }
    return results


def compute_houses(jd_ut: float, latitude: float, longitude: float, sidereal: bool, house_system: bytes = b"P"):
    """Computes ascendant, midheaven, and house cusps (Placidus by default)."""
    if sidereal:
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        cusps, ascmc = swe.houses_ex(jd_ut, latitude, longitude, house_system, flags=swe.FLG_SIDEREAL)
    else:
        cusps, ascmc = swe.houses(jd_ut, latitude, longitude, house_system)

    asc_sign, asc_deg = _sign_of(ascmc[0])
    mc_sign, mc_deg = _sign_of(ascmc[1])
    return {
        "ascendant": {"longitude": round(ascmc[0] % 360.0, 4), "sign": asc_sign, "degree_in_sign": asc_deg},
        "midheaven": {"longitude": round(ascmc[1] % 360.0, 4), "sign": mc_sign, "degree_in_sign": mc_deg},
        "cusps": [round(c % 360.0, 4) for c in cusps],
    }


def whole_sign_house_of(planet_longitude: float, ascendant_sign: str) -> int:
    """Traditional Vedic whole-sign house placement: house = offset of planet's sign from ascendant's sign."""
    planet_sign, _ = _sign_of(planet_longitude)
    asc_idx = ZODIAC_SIGNS.index(ascendant_sign)
    planet_idx = ZODIAC_SIGNS.index(planet_sign)
    return ((planet_idx - asc_idx) % 12) + 1


def quadrant_house_of(planet_longitude: float, cusps: List[float]) -> int:
    """Placidus/quadrant house placement: finds which cusp interval a planet's longitude falls in."""
    lon = planet_longitude % 360.0
    for i in range(12):
        start = cusps[i]
        end = cusps[(i + 1) % 12]
        if start < end:
            if start <= lon < end:
                return i + 1
        else:  # interval wraps past 360/0
            if lon >= start or lon < end:
                return i + 1
    return 12


def nakshatra_of(moon_longitude: float) -> Dict[str, Any]:
    """Computes the Moon's nakshatra (lunar mansion) and pada (quarter) — a core Vedic placement."""
    lon = moon_longitude % 360.0
    index = int(lon // NAKSHATRA_SPAN_DEG)
    index = min(index, len(NAKSHATRAS) - 1)
    remainder = lon - index * NAKSHATRA_SPAN_DEG
    pada = int(remainder // NAKSHATRA_PADA_SPAN_DEG) + 1
    return {"name": NAKSHATRAS[index], "pada": pada}


def sign_profile(sign: str) -> Dict[str, str]:
    return {"element": SIGN_ELEMENT.get(sign, ""), "modality": SIGN_MODALITY.get(sign, "")}


def compute_aspects(planet_positions: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Finds major Ptolemaic aspects (conjunction/sextile/square/trine/opposition) between planet pairs."""
    names = list(planet_positions.keys())
    aspects = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            lon_a = planet_positions[a]["longitude"]
            lon_b = planet_positions[b]["longitude"]
            diff = abs(lon_a - lon_b) % 360.0
            if diff > 180:
                diff = 360 - diff
            for aspect_name, (angle, orb) in MAJOR_ASPECTS.items():
                if abs(diff - angle) <= orb:
                    aspects.append({
                        "planets": [a, b],
                        "aspect": aspect_name,
                        "orb": round(abs(diff - angle), 2),
                    })
                    break
    return aspects
