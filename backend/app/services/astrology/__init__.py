"""
Astrology subsystem for Aetheria.

Modular, swappable calculation pipeline for Vedic (sidereal) and
Western (tropical) birth charts, built on the Swiss Ephemeris engine
(pyswisseph) rather than hardcoded planetary tables.

Public entry point: `birth_chart_service` (see birth_chart_service.py).
"""

from backend.app.services.astrology.birth_chart_service import birth_chart_service

__all__ = ["birth_chart_service"]
