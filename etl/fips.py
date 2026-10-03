"""County identity: the TIGER county list, name normalization, and Connecticut crosswalks."""
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

# Contiguous US plus DC.
EXCLUDED_STATE_FIPS = {"02", "15", "60", "66", "69", "72", "78"}

# Connecticut replaced its 8 counties with 9 planning regions in 2022. TIGER 2024, ACS 2023,
# and NRI v1.20 use regions. CMRA, the Esri FCC layer, LBNL, and FracTracker use counties.
# Both maps are dominant-overlap approximations, not area-weighted.
# Region -> county it mostly sits in. Use for rates and scores.
CT_REGION_TO_OLD = {
    "09110": "09003",  # Capitol -> Hartford
    "09120": "09001",  # Greater Bridgeport -> Fairfield
    "09130": "09007",  # Lower Connecticut River Valley -> Middlesex
    "09140": "09009",  # Naugatuck Valley -> New Haven
    "09150": "09015",  # Northeastern Connecticut -> Windham
    "09160": "09005",  # Northwest Hills -> Litchfield
    "09170": "09009",  # South Central Connecticut -> New Haven
    "09180": "09011",  # Southeastern Connecticut -> New London
    "09190": "09001",  # Western Connecticut -> Fairfield
}
# County -> region holding most of it. Use for counts and sums.
CT_OLD_TO_REGION = {
    "09001": "09190", "09003": "09110", "09005": "09160", "09007": "09130",
    "09009": "09170", "09011": "09180", "09013": "09110", "09015": "09150",
}
CT_OLD_NAMES = {
    "Fairfield": "09001", "Hartford": "09003", "Litchfield": "09005", "Middlesex": "09007",
    "New Haven": "09009", "New London": "09011", "Tolland": "09013", "Windham": "09015",
}

_SUFFIXES = (" county", " parish", " borough", " census area", " municipality",
             " planning region")


def load_tiger(raw_dir):
    """County list for the contiguous US plus DC from the TIGER cartographic boundary file."""
    g = gpd.read_file(Path(raw_dir) / "tiger/cb_2024_us_county_500k.zip", ignore_geometry=True)
    return g[~g.STATEFP.isin(EXCLUDED_STATE_FIPS)].sort_values("GEOID").reset_index(drop=True)


def normalize_county(name, state):
    """Return a join key for a county name, such as ("St. Louis County", "MO") -> "MO|saintlouis".

    Strips "County", "Parish", and similar suffixes. Keeps a trailing "city" so that Virginia
    independent cities stay distinct from same-named counties.
    """
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode().lower().strip()
    s = re.sub(r"[.'`]", "", s)
    for suffix in _SUFFIXES:
        if s.endswith(suffix):
            s = s[: -len(suffix)]
            break
    s = re.sub(r"\bst\b", "saint", s)
    s = re.sub(r"\bste\b", "sainte", s)
    return f"{str(state).strip().upper()}|{re.sub(r'[^a-z0-9]', '', s)}"


def build_lookup(tiger):
    """Map normalize_county keys to FIPS for every TIGER county, plus old Connecticut counties."""
    lookup = {normalize_county(n, s): f
              for n, s, f in zip(tiger.NAMELSAD, tiger.STUSPS, tiger.GEOID)}
    for name, old in CT_OLD_NAMES.items():
        lookup[normalize_county(name, "CT")] = CT_OLD_TO_REGION[old]
    return lookup


def to_fips(name, state, lookup):
    """FIPS for a county name, or None. Tries the name as given, then as an independent city."""
    key = normalize_county(name, state)
    return lookup.get(key) or lookup.get(key + "city")


def ct_rates_to_regions(df):
    """Re-key rows for old Connecticut counties onto planning regions. For rates and scores."""
    old = df.set_index("fips")
    regions = old.reindex(list(CT_REGION_TO_OLD.values()))
    regions.index = list(CT_REGION_TO_OLD.keys())
    out = old[~old.index.isin(CT_OLD_TO_REGION)]
    return pd.concat([out, regions]).rename_axis("fips").reset_index()
