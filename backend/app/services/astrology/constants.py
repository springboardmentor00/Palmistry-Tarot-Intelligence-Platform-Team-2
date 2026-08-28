"""
Static reference tables used by the astrology engine.

Nothing in this file is a calculated result — signs, nakshatras, and
aspect definitions are fixed astronomical/astrological conventions,
not planetary positions. Actual planetary positions are always
computed at request time in `engine.py` via Swiss Ephemeris.
"""

ZODIAC_SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_ELEMENT = {
    "Aries": "Fire", "Leo": "Fire", "Sagittarius": "Fire",
    "Taurus": "Earth", "Virgo": "Earth", "Capricorn": "Earth",
    "Gemini": "Air", "Libra": "Air", "Aquarius": "Air",
    "Cancer": "Water", "Scorpio": "Water", "Pisces": "Water",
}

SIGN_MODALITY = {
    "Aries": "Cardinal", "Cancer": "Cardinal", "Libra": "Cardinal", "Capricorn": "Cardinal",
    "Taurus": "Fixed", "Leo": "Fixed", "Scorpio": "Fixed", "Aquarius": "Fixed",
    "Gemini": "Mutable", "Virgo": "Mutable", "Sagittarius": "Mutable", "Pisces": "Mutable",
}

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

NAKSHATRA_SPAN_DEG = 360.0 / len(NAKSHATRAS)  # 13deg 20'
NAKSHATRA_PADA_SPAN_DEG = NAKSHATRA_SPAN_DEG / 4.0  # 3deg 20'

# Major aspects: name -> (angle degrees, default orb degrees)
MAJOR_ASPECTS = {
    "Conjunction": (0, 8),
    "Sextile": (60, 4),
    "Square": (90, 6),
    "Trine": (120, 6),
    "Opposition": (180, 8),
}

HOUSE_MEANINGS = {
    1: "Self, identity, and outward approach to life",
    2: "Personal resources, values, and finances",
    3: "Communication, immediate environment, and learning",
    4: "Home, roots, and emotional foundation",
    5: "Creativity, self-expression, and romance",
    6: "Daily habits, routine, wellness, and service",
    7: "Partnerships and one-on-one relationships",
    8: "Shared resources, transformation, and depth",
    9: "Beliefs, higher learning, and long-distance/spiritual growth",
    10: "Career, public reputation, and life direction",
    11: "Community, long-term goals, and networks",
    12: "Inner life, subconscious patterns, and release",
}
