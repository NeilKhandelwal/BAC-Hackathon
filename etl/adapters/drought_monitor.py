"""US Drought Monitor: share of weeks in D2 or worse, 2000 to 2025."""
import io
from pathlib import Path

import pandas as pd
import requests

from etl.fips import ct_rates_to_regions, load_tiger

SOURCE = {"name": "US Drought Monitor", "version": "weekly county statistics, 2000-2025",
          "url": "https://usdmdataservices.unl.edu/api/CountyStatistics/GetDroughtSeverityStatisticsByAreaPercent"}
RAW = "usdm"
NOTES = ["drought_share_weeks_d2plus is the mean weekly percent of county area in D2 or worse, "
         "so it weights weeks by area."]


def fetch(raw_dir):
    """One call per state. Each response is about 12 MB, so only the county means are cached."""
    out = Path(raw_dir) / RAW
    out.mkdir(parents=True, exist_ok=True)
    for state in sorted(load_tiger(raw_dir).STUSPS.unique()):
        dest = out / f"{state}.csv"
        if dest.exists():
            continue
        r = requests.get(SOURCE["url"], headers={"Accept": "text/csv"}, timeout=300, params={
            "aoi": state, "startdate": "1/1/2000", "enddate": "12/31/2025", "statisticsType": 1})
        r.raise_for_status()
        weekly = pd.read_csv(io.StringIO(r.text), dtype={"FIPS": str})
        if weekly.empty:
            raise RuntimeError(f"Drought Monitor returned no rows for {state}")
        # statisticsType=1 is cumulative: D2 already includes D3 and D4.
        weekly.groupby("FIPS").agg(mean_d2_pct=("D2", "mean"), weeks=("D2", "size")).to_csv(dest)


def build(raw_dir):
    df = pd.concat(pd.read_csv(f, dtype={"FIPS": str}) for f in sorted((Path(raw_dir) / RAW).glob("*.csv")))
    out = pd.DataFrame({"fips": df.FIPS.str.zfill(5), "drought_share_weeks_d2plus": df.mean_d2_pct / 100})
    if out.fips.isin(["09001"]).any():
        out = ct_rates_to_regions(out)
    return out
