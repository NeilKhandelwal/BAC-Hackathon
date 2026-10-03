"""Long-run population decline: population now against the county's census peak since 1950."""
from pathlib import Path

import pandas as pd

from etl.download import download
from etl.fips import ct_rates_to_regions, load_tiger

SOURCE = {"name": "Census Population of Counties by Decennial Census 1900-1990 (Forstall), NBER mirror",
          "version": "1995 file; plus Census 2000 and 2010 counts and Vintage 2024 estimates",
          "url": "https://data.nber.org/census/population/cencounts/cencounts.csv"}
RAW = "cencounts/cencounts.csv"
URL_2000 = "https://www2.census.gov/programs-surveys/popest/datasets/2000-2010/intercensal/county/co-est00int-tot.csv"
NOTES = ["pop_change_pct_since_peak compares the July 2024 estimate with the highest census count "
         "from 1950 to 2020. It is 0 for counties at their peak now. 1950-1990 come from the Census "
         "Bureau's Forstall table, which census.gov no longer hosts, so the NBER mirror is used. "
         "2000 is the Census 2000 estimates base, 2010 the census count, and 2020 the Vintage 2024 "
         "estimates base: no keyless file of raw 2020 county counts was found.",
         "Counties that merged or consolidated since 1950 have their earlier populations summed "
         "into today's county (Virginia city consolidations, Dade, Shannon, and two South Dakota "
         "counties). Smaller boundary changes and annexations are not adjusted.",
         "Broomfield, CO (08014) has no count before 2000, so its peak is taken from 2000 on.",
         "Connecticut is computed on its 8 old counties, with the July 2020 estimate as the "
         "current value, and each planning region takes the value of the county it mostly "
         "overlaps (etl/fips.py CT_REGION_TO_OLD)."]

# Old FIPS -> today's county, for counties absorbed since 1950. Populations are summed.
MERGED = {"12025": "12086",  # Dade -> Miami-Dade
          "46113": "46102",  # Shannon -> Oglala Lakota
          "46131": "46071",  # Washabaugh -> Jackson, SD (1983)
          "46001": "46041",  # Armstrong -> Dewey, SD (1952)
          "51515": "51019",  # Bedford city -> Bedford County (2013)
          "51560": "51005",  # Clifton Forge -> Alleghany (2001)
          "51780": "51083",  # South Boston -> Halifax (1995)
          "51055": "51650",  # Elizabeth City County -> Hampton (1952)
          "51189": "51700",  # Warwick -> Newport News (1958)
          "51123": "51800",  # Nansemond -> Suffolk (1974)
          "51129": "51550",  # Norfolk County -> Chesapeake (1963)
          "51785": "51550",  # South Norfolk -> Chesapeake (1963)
          "51151": "51810"}  # Princess Anne -> Virginia Beach (1963)
DECADES = ["pop1950", "pop1960", "pop1970", "pop1980", "pop1990"]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e5)
    download(URL_2000, Path(raw_dir) / "popest/co-est00int-tot.csv", 1e5)
    # Vintage 2020 and 2024 files come from the popest adapter's fetch.


def _popest(path, columns):
    df = pd.read_csv(path, encoding="latin1", dtype={"STATE": str, "COUNTY": str})
    df = df[df.SUMLEV == 50]
    df.index = df.STATE.str.zfill(2) + df.COUNTY.str.zfill(3)
    return df[columns].apply(pd.to_numeric, errors="coerce")


def build(raw_dir):
    raw = Path(raw_dir)
    f = pd.read_csv(raw / RAW, dtype={"fips": str}, na_values=".")
    f = f[~f.fips.str.contains(r"\.") & ~f.fips.str.endswith("000")].set_index("fips")[DECADES]
    y00 = _popest(raw / "popest/co-est00int-tot.csv", ["ESTIMATESBASE2000"])
    y10 = _popest(raw / "popest/co-est2020-alldata.csv", ["CENSUS2010POP", "POPESTIMATE2020"])
    y20 = _popest(raw / "popest/co-est2024-alldata.csv", ["ESTIMATESBASE2020", "POPESTIMATE2024"])
    counts = f.join(y00, how="outer").join(y10.CENSUS2010POP, how="outer")
    # min_count=1 keeps a county with no count in a year null, not 0.
    counts = counts.groupby(lambda x: MERGED.get(x, x)).sum(min_count=1)

    ct = counts.index.str.startswith("09")
    old_ct = counts[ct].max(axis=1)
    y20 = y20[~y20.index.str.startswith("09")]  # Connecticut regions: handled through old counties
    rest = counts[~ct].join(y20.ESTIMATESBASE2020, how="outer").max(axis=1)
    change = pd.concat([y20.POPESTIMATE2024 / rest, y10.POPESTIMATE2020[old_ct.index] / old_ct])
    pct = (100 * (change - 1)).clip(upper=0).dropna()
    out = ct_rates_to_regions(pd.DataFrame({"fips": pct.index, "pop_change_pct_since_peak": pct.values}))
    return out[out.fips.isin(set(load_tiger(raw_dir).GEOID))]
