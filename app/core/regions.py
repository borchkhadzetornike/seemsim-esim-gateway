"""Country-to-region mapping and classification for eSIM packages.

Regions follow eSIM Access's multi-area plan grouping:
  - Europe
  - Americas (North + South America + Caribbean)
  - Asia
  - Africa
  - Oceania
  - Middle East
  - Worldwide (packages spanning 3+ distinct regions)
"""

from __future__ import annotations

from collections import Counter

COUNTRY_TO_REGION: dict[str, str] = {
    # ── Europe ───────────────────────────────────────────────────────
    "AL": "europe", "AD": "europe", "AT": "europe", "BY": "europe",
    "BE": "europe", "BA": "europe", "BG": "europe", "HR": "europe",
    "CY": "europe", "CZ": "europe", "DK": "europe", "EE": "europe",
    "FI": "europe", "FR": "europe", "DE": "europe", "GR": "europe",
    "HU": "europe", "IS": "europe", "IE": "europe", "IT": "europe",
    "XK": "europe", "LV": "europe", "LI": "europe", "LT": "europe",
    "LU": "europe", "MT": "europe", "MD": "europe", "MC": "europe",
    "ME": "europe", "NL": "europe", "MK": "europe", "NO": "europe",
    "PL": "europe", "PT": "europe", "RO": "europe", "RU": "europe",
    "SM": "europe", "RS": "europe", "SK": "europe", "SI": "europe",
    "ES": "europe", "SE": "europe", "CH": "europe", "UA": "europe",
    "GB": "europe", "VA": "europe", "FO": "europe", "GI": "europe",
    "GG": "europe", "IM": "europe", "JE": "europe", "AX": "europe",
    "SJ": "europe",

    # ── Americas (North + South America + Caribbean) ─────────────────
    "AG": "americas", "BS": "americas", "BB": "americas",
    "BZ": "americas", "CA": "americas", "CR": "americas",
    "CU": "americas", "DM": "americas", "DO": "americas",
    "SV": "americas", "GD": "americas", "GT": "americas",
    "HT": "americas", "HN": "americas", "JM": "americas",
    "MX": "americas", "NI": "americas", "PA": "americas",
    "KN": "americas", "LC": "americas", "VC": "americas",
    "TT": "americas", "US": "americas", "PR": "americas",
    "VI": "americas", "GL": "americas", "BM": "americas",
    "KY": "americas", "AW": "americas", "CW": "americas",
    "SX": "americas", "BQ": "americas", "TC": "americas",
    "VG": "americas", "AI": "americas", "MS": "americas",
    "GP": "americas", "MQ": "americas", "BL": "americas",
    "MF": "americas", "PM": "americas",
    "AR": "americas", "BO": "americas", "BR": "americas",
    "CL": "americas", "CO": "americas", "EC": "americas",
    "FK": "americas", "GF": "americas", "GY": "americas",
    "PY": "americas", "PE": "americas", "SR": "americas",
    "UY": "americas", "VE": "americas",
    "AN": "americas",

    # ── Asia ──────────────────────────────────────────────────────────
    "AF": "asia", "AM": "asia", "AZ": "asia", "BD": "asia",
    "BT": "asia", "BN": "asia", "KH": "asia", "CN": "asia",
    "GE": "asia", "HK": "asia", "IN": "asia", "ID": "asia",
    "JP": "asia", "KZ": "asia", "KG": "asia", "LA": "asia",
    "MO": "asia", "MY": "asia", "MV": "asia", "MN": "asia",
    "MM": "asia", "NP": "asia", "KP": "asia", "PK": "asia",
    "PH": "asia", "SG": "asia", "KR": "asia", "LK": "asia",
    "TW": "asia", "TJ": "asia", "TH": "asia", "TL": "asia",
    "TM": "asia", "UZ": "asia", "VN": "asia",

    # ── Africa ────────────────────────────────────────────────────────
    "DZ": "africa", "AO": "africa", "BJ": "africa", "BW": "africa",
    "BF": "africa", "BI": "africa", "CV": "africa", "CM": "africa",
    "CF": "africa", "TD": "africa", "KM": "africa", "CG": "africa",
    "CD": "africa", "CI": "africa", "DJ": "africa", "EG": "africa",
    "GQ": "africa", "ER": "africa", "SZ": "africa", "ET": "africa",
    "GA": "africa", "GM": "africa", "GH": "africa", "GN": "africa",
    "GW": "africa", "KE": "africa", "LS": "africa", "LR": "africa",
    "LY": "africa", "MG": "africa", "MW": "africa", "ML": "africa",
    "MR": "africa", "MU": "africa", "MA": "africa", "MZ": "africa",
    "NA": "africa", "NE": "africa", "NG": "africa", "RW": "africa",
    "ST": "africa", "SN": "africa", "SC": "africa", "SL": "africa",
    "SO": "africa", "ZA": "africa", "SS": "africa", "SD": "africa",
    "TZ": "africa", "TG": "africa", "TN": "africa", "UG": "africa",
    "ZM": "africa", "ZW": "africa", "RE": "africa", "YT": "africa",
    "SH": "africa",

    # ── Oceania ───────────────────────────────────────────────────────
    "AU": "oceania", "FJ": "oceania", "KI": "oceania", "MH": "oceania",
    "FM": "oceania", "NR": "oceania", "NZ": "oceania", "PW": "oceania",
    "PG": "oceania", "WS": "oceania", "SB": "oceania", "TO": "oceania",
    "TV": "oceania", "VU": "oceania", "NC": "oceania", "PF": "oceania",
    "GU": "oceania", "AS": "oceania", "CK": "oceania", "NU": "oceania",
    "TK": "oceania", "WF": "oceania", "NF": "oceania", "MP": "oceania",

    # ── Middle East ───────────────────────────────────────────────────
    "BH": "middle_east", "IR": "middle_east", "IQ": "middle_east",
    "IL": "middle_east", "JO": "middle_east", "KW": "middle_east",
    "LB": "middle_east", "OM": "middle_east", "PS": "middle_east",
    "QA": "middle_east", "SA": "middle_east", "SY": "middle_east",
    "TR": "middle_east", "AE": "middle_east", "YE": "middle_east",
}

REGION_DISPLAY_NAMES: dict[str, str] = {
    "europe": "Europe",
    "americas": "America & Canada",
    "asia": "Asia",
    "africa": "Africa",
    "oceania": "Oceania",
    "middle_east": "Middle East",
    "worldwide": "Worldwide",
}

_MULTI_REGION_THRESHOLD = 3


def classify_region(countries: list[str]) -> str:
    """Determine the dominant region for a list of country codes.

    Returns "worldwide" when the package spans 3+ distinct regions.
    For two regions, returns the most common one.
    """
    if not countries:
        return "worldwide"

    regions = [COUNTRY_TO_REGION[cc] for cc in countries if cc in COUNTRY_TO_REGION]

    if not regions:
        return "worldwide"

    counts = Counter(regions)
    distinct = len(counts)

    if distinct == 1:
        return regions[0]
    if distinct >= _MULTI_REGION_THRESHOLD:
        return "worldwide"

    return counts.most_common(1)[0][0]


def get_region_display_name(region_code: str) -> str:
    """Return a human-readable label for a region code."""
    return REGION_DISPLAY_NAMES.get(region_code, region_code.replace("_", " ").title())
