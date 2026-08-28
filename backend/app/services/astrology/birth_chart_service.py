"""
High-level Birth Chart service.

Orchestrates location resolution + the ephemeris engine to produce
structured Vedic and Western birth charts from raw birth details.
Output is a plain, JSON-serializable dict designed to be stored as-is
(see BirthChart.vedic_chart / BirthChart.western_chart JSON columns)
and consumed downstream by the AI interpretation pipeline.
"""

import datetime
from typing import Dict, Any, Optional

from backend.app.services.astrology import engine
from backend.app.services.astrology.locations import resolve_location
from backend.app.services.astrology.constants import HOUSE_MEANINGS, SIGN_ELEMENT, SIGN_MODALITY


class BirthChartService:

    def generate(
        self,
        birth_date: datetime.date,
        birth_time: datetime.time,
        birth_place: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timezone_offset_hours: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generates both a Vedic (sidereal, whole-sign) and Western (tropical,
        Placidus) birth chart for the given birth details. Returns a dict with
        keys: resolved_location, vedic_chart, western_chart.
        """
        location = resolve_location(birth_place, latitude, longitude, timezone_offset_hours)
        jd_ut = engine.to_julian_day_ut(birth_date, birth_time, location["timezone_offset_hours"])

        vedic_chart = self._build_vedic_chart(jd_ut, location)
        western_chart = self._build_western_chart(jd_ut, location)

        return {
            "resolved_location": {**location, "place_name": birth_place},
            "vedic_chart": vedic_chart,
            "western_chart": western_chart,
        }

    # ------------------------------------------------------------------
    # Vedic (sidereal / Lahiri ayanamsa / whole-sign houses)
    # ------------------------------------------------------------------
    def _build_vedic_chart(self, jd_ut: float, location: Dict[str, float]) -> Dict[str, Any]:
        planets = engine.compute_planets(jd_ut, sidereal=True)
        houses = engine.compute_houses(
            jd_ut, location["latitude"], location["longitude"], sidereal=True
        )
        asc_sign = houses["ascendant"]["sign"]

        placements = {}
        for name in engine.VEDIC_PLANETS:
            data = planets[name]
            house_num = engine.whole_sign_house_of(data["longitude"], asc_sign)
            placements[name] = {
                **data,
                "house": house_num,
                "house_meaning": HOUSE_MEANINGS.get(house_num, ""),
            }

        moon_nakshatra = engine.nakshatra_of(planets["Moon"]["longitude"])
        aspects = engine.compute_aspects({k: planets[k] for k in engine.VEDIC_PLANETS if k in planets})

        return {
            "zodiac_type": "sidereal",
            "ayanamsa": "Lahiri",
            "house_system": "whole_sign",
            "ascendant": houses["ascendant"],
            "planets": placements,
            "moon_nakshatra": moon_nakshatra,
            "major_aspects": aspects,
        }

    # ------------------------------------------------------------------
    # Western (tropical / Placidus houses)
    # ------------------------------------------------------------------
    def _build_western_chart(self, jd_ut: float, location: Dict[str, float]) -> Dict[str, Any]:
        planets = engine.compute_planets(jd_ut, sidereal=False)
        houses = engine.compute_houses(
            jd_ut, location["latitude"], location["longitude"], sidereal=False
        )
        cusps = houses["cusps"]

        placements = {}
        for name in engine.WESTERN_PLANETS:
            data = planets[name]
            house_num = engine.quadrant_house_of(data["longitude"], cusps)
            placements[name] = {
                **data,
                "house": house_num,
                "house_meaning": HOUSE_MEANINGS.get(house_num, ""),
                "element": SIGN_ELEMENT.get(data["sign"], ""),
                "modality": SIGN_MODALITY.get(data["sign"], ""),
            }

        aspects = engine.compute_aspects({k: planets[k] for k in engine.WESTERN_PLANETS if k in planets})

        return {
            "zodiac_type": "tropical",
            "house_system": "placidus",
            "ascendant": houses["ascendant"],
            "midheaven": houses["midheaven"],
            "planets": placements,
            "sun_sign": planets["Sun"]["sign"],
            "moon_sign": planets["Moon"]["sign"],
            "rising_sign": houses["ascendant"]["sign"],
            "major_aspects": aspects,
        }

    # ------------------------------------------------------------------
    # Summarization for downstream AI / dashboard consumption
    # ------------------------------------------------------------------
    def summarize_for_ai(self, chart_bundle: Dict[str, Any]) -> str:
        """Renders a compact, deterministic natural-language digest of a chart bundle for prompt context."""
        vedic = chart_bundle.get("vedic_chart", {})
        western = chart_bundle.get("western_chart", {})
        lines = []

        if western:
            lines.append(
                f"Western tropical chart: Sun in {western.get('sun_sign', '?')}, "
                f"Moon in {western.get('moon_sign', '?')}, Rising sign {western.get('rising_sign', '?')}."
            )
            key_aspects = western.get("major_aspects", [])[:5]
            if key_aspects:
                aspect_desc = "; ".join(
                    f"{a['planets'][0]}-{a['planets'][1]} {a['aspect']}" for a in key_aspects
                )
                lines.append(f"Key Western aspects: {aspect_desc}.")

        if vedic:
            asc = vedic.get("ascendant", {}).get("sign", "?")
            moon = vedic.get("planets", {}).get("Moon", {})
            nak = vedic.get("moon_nakshatra", {})
            lines.append(
                f"Vedic sidereal chart (Lahiri): Lagna (Ascendant) in {asc}, "
                f"Moon in {moon.get('sign', '?')} (house {moon.get('house', '?')}), "
                f"Nakshatra {nak.get('name', '?')} pada {nak.get('pada', '?')}."
            )

        return " ".join(lines)


birth_chart_service = BirthChartService()
