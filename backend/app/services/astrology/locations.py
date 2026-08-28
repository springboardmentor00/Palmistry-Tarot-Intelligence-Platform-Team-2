"""
Location resolution helper for birth charts.

Precise chart calculation needs latitude, longitude, and UTC offset
at the birth moment. This module resolves those from an explicit
lat/lon/timezone if the caller supplies them (always preferred and
most accurate), and otherwise falls back to a small convenience
lookup table of major city names so a user can type a familiar place
name during testing/demoing without wiring up a full geocoding
integration. This is reference lookup data (coordinates of fixed
cities), not calculated astrological output, so it does not conflict
with the "no hardcoded planetary positions" requirement.

A real geocoding/timezone API (e.g. a Google/OpenCage + timezonefinder
integration) can be dropped in later by extending `resolve_location`
without touching the calculation engine.
"""

from typing import Optional, Dict, Any

# name (lowercased) -> (latitude, longitude, standard UTC offset hours)
KNOWN_LOCATIONS: Dict[str, Any] = {
    "bhubaneswar": (20.2961, 85.8245, 5.5),
    "delhi": (28.6139, 77.2090, 5.5),
    "new delhi": (28.6139, 77.2090, 5.5),
    "mumbai": (19.0760, 72.8777, 5.5),
    "kolkata": (22.5726, 88.3639, 5.5),
    "chennai": (13.0827, 80.2707, 5.5),
    "bengaluru": (12.9716, 77.5946, 5.5),
    "bangalore": (12.9716, 77.5946, 5.5),
    "hyderabad": (17.3850, 78.4867, 5.5),
    "pune": (18.5204, 73.8567, 5.5),
    "new york": (40.7128, -74.0060, -5.0),
    "los angeles": (34.0522, -118.2437, -8.0),
    "london": (51.5072, -0.1276, 0.0),
    "paris": (48.8566, 2.3522, 1.0),
    "tokyo": (35.6762, 139.6503, 9.0),
    "singapore": (1.3521, 103.8198, 8.0),
    "dubai": (25.2048, 55.2708, 4.0),
    "sydney": (-33.8688, 151.2093, 10.0),
    "toronto": (43.6532, -79.3832, -5.0),
    "berlin": (52.5200, 13.4050, 1.0),
}


def resolve_location(
    place_name: Optional[str],
    latitude: Optional[float],
    longitude: Optional[float],
    timezone_offset_hours: Optional[float],
) -> Dict[str, float]:
    """
    Resolves final (latitude, longitude, timezone_offset_hours) to use for chart
    calculation. Explicit coordinates always take precedence over the name lookup.
    Raises ValueError if nothing usable can be resolved.
    """
    if latitude is not None and longitude is not None and timezone_offset_hours is not None:
        return {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "timezone_offset_hours": float(timezone_offset_hours),
        }

    if place_name:
        match = KNOWN_LOCATIONS.get(place_name.strip().lower())
        if match:
            lat, lon, tz = match
            return {
                "latitude": latitude if latitude is not None else lat,
                "longitude": longitude if longitude is not None else lon,
                "timezone_offset_hours": (
                    timezone_offset_hours if timezone_offset_hours is not None else tz
                ),
            }

    raise ValueError(
        "Could not resolve a precise location. Provide latitude, longitude, and "
        "timezone_offset_hours explicitly, or use a recognized birth_place name."
    )
