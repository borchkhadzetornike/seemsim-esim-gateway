"""Country-to-continent mapping and region classification for eSIM packages."""

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

    # ── North America ────────────────────────────────────────────────
    "AG": "north_america", "BS": "north_america", "BB": "north_america",
    "BZ": "north_america", "CA": "north_america", "CR": "north_america",
    "CU": "north_america", "DM": "north_america", "DO": "north_america",
    "SV": "north_america", "GD": "north_america", "GT": "north_america",
    "HT": "north_america", "HN": "north_america", "JM": "north_america",
    "MX": "north_america", "NI": "north_america", "PA": "north_america",
    "KN": "north_america", "LC": "north_america", "VC": "north_america",
    "TT": "north_america", "US": "north_america", "PR": "north_america",
    "VI": "north_america", "GL": "north_america", "BM": "north_america",
    "KY": "north_america", "AW": "north_america", "CW": "north_america",
    "SX": "north_america", "BQ": "north_america", "TC": "north_america",
    "VG": "north_america", "AI": "north_america", "MS": "north_america",
    "GP": "north_america", "MQ": "north_america", "BL": "north_america",
    "MF": "north_america", "PM": "north_america",

    # ── South America ────────────────────────────────────────────────
    "AR": "south_america", "BO": "south_america", "BR": "south_america",
    "CL": "south_america", "CO": "south_america", "EC": "south_america",
    "FK": "south_america", "GF": "south_america", "GY": "south_america",
    "PY": "south_america", "PE": "south_america", "SR": "south_america",
    "UY": "south_america", "VE": "south_america",

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

    # ── Caribbean ─────────────────────────────────────────────────────
    "AN": "caribbean", "HK": "caribbean",  # HK already mapped; kept for reference
}

# Override duplicate: HK → asia takes precedence (dict last-write wins above,
# so fix by re-assigning after the initial block).
COUNTRY_TO_REGION["HK"] = "asia"


REGION_DISPLAY_NAMES: dict[str, str] = {
    "europe": "Europe",
    "asia": "Asia",
    "north_america": "North America",
    "south_america": "South America",
    "africa": "Africa",
    "oceania": "Oceania",
    "middle_east": "Middle East",
    "caribbean": "Caribbean",
    "worldwide": "Worldwide",
}

_MULTI_REGION_THRESHOLD = 3


def classify_region(countries: list[str]) -> str:
    """Determine the dominant region for a list of ISO-3166-1 alpha-2 country codes.

    Returns the single region if all mapped countries fall within one region,
    or "worldwide" when the package spans ``_MULTI_REGION_THRESHOLD`` or more
    distinct regions.  For two distinct regions, returns the most common one.
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

    # Two distinct regions → return the dominant one
    return counts.most_common(1)[0][0]


def get_region_display_name(region_code: str) -> str:
    """Return a human-readable label for a region code."""
    return REGION_DISPLAY_NAMES.get(region_code, region_code.replace("_", " ").title())
