"""BEA county employment by industry: manufacturing's share of jobs in 1969 and its change to 2022."""
import re
import zipfile
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import build_lookup, ct_rates_to_regions, load_tiger, normalize_county, to_fips

SOURCE = {"name": "BEA CAEMP25 county employment by industry", "version": "CAEMP25S 1969 (SIC), CAEMP25N 2022 (NAICS)",
          "url": "https://apps.bea.gov/regional/zip/CAEMP25S.zip"}
RAW = "bea/CAEMP25S.zip"
URL_2022 = "https://apps.bea.gov/regional/zip/CAEMP25N.zip"
NOTES = ["Manufacturing shares divide BEA manufacturing jobs by BEA total employment, which "
         "includes proprietors and government. 1969 uses SIC Manufacturing (line 400), 2022 uses "
         "NAICS Manufacturing (line 500). The two definitions differ slightly: NAICS moved "
         "publishing out of manufacturing.",
         "BEA withholds some county cells, marked (D), (NA), or (L). Those counties are null: "
         "103 for the 1969 share and 378 for the 1969-2022 change, mostly from 2022 suppression.",
         "BEA combines 23 Virginia independent cities with neighboring counties, and Shawano with "
         "Menominee, WI, in 1969. Each member takes the combined area's share.",
         "BEA reports the 8 old Connecticut counties. Each planning region takes the share of the "
         "county it mostly overlaps (etl/fips.py CT_REGION_TO_OLD)."]


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)
    download(URL_2022, Path(raw_dir) / "bea/CAEMP25N.zip", 1e6, ZIP_MAGIC)


def _members(fips, name, lookup):
    """FIPS codes a BEA area covers. A combined area, like 'Augusta, Staunton + Waynesboro, VA*',
    covers every named county or city."""
    if not re.match(r"519\d\d|55901", fips):
        return [fips]
    if fips == "55901":
        return ["55115", "55078"]  # Shawano (includes Menominee)
    names, state = name.rstrip("*").rsplit(", ", 1)
    first, *cities = [n.strip() for n in re.split(r",|\+", names)]
    # Members after the first are independent cities. "Southampton + Franklin" means Franklin
    # city (51620), not Franklin County.
    members = [to_fips(first, state, lookup)] + [
        lookup.get(normalize_county(c, state) + "city") or to_fips(c, state, lookup) for c in cities]
    if None in members:
        raise ValueError(f"BEA area {fips} {name!r}: a member name didn't match a county")
    return members


def _share(path, member, year, line, lookup):
    with zipfile.ZipFile(path) as z, z.open(member) as f:
        d = pd.read_csv(f, dtype=str, encoding="latin1", usecols=["GeoFIPS", "GeoName", "LineCode", year])
    d["GeoFIPS"] = d.GeoFIPS.str.strip().str.strip('"')
    d = d[~d.GeoFIPS.str.endswith("000")]
    value = pd.to_numeric(d[year].str.strip(), errors="coerce")  # (D), (NA), (L) -> null
    by_line = d.assign(v=value).pivot_table(index=["GeoFIPS", "GeoName"], columns=d.LineCode.str.strip(),
                                            values="v", aggfunc="first")
    share = (by_line[line] / by_line["10"]).reset_index(name="share")
    rows = [(m, m != f, s) for f, n, s in share.itertuples(index=False) for m in _members(f, n, lookup)]
    rows = pd.DataFrame(rows, columns=["fips", "from_combined", "share"])
    # A county's own row wins when it has a value. BEA lists Shawano and Menominee both alone
    # and combined.
    return rows.sort_values("from_combined").groupby("fips").share.first()


def build(raw_dir):
    raw = Path(raw_dir) / "bea"
    tiger = load_tiger(raw_dir)
    lookup = build_lookup(tiger)
    s69 = _share(raw / "CAEMP25S.zip", "CAEMP25S__ALL_AREAS_1969_2000.csv", "1969", "400", lookup)
    s22 = _share(raw / "CAEMP25N.zip", "CAEMP25N__ALL_AREAS_2001_2022.csv", "2022", "500", lookup)
    out = pd.DataFrame({"mfg_emp_share_1969": s69, "mfg_emp_share_change_1969_2022": s22 - s69})
    out = ct_rates_to_regions(out.rename_axis("fips").reset_index())
    return out[out.fips.isin(set(tiger.GEOID))]
