"""LBNL Queued Up 2026: interconnection queue volume, age, and outcomes by county."""
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import CT_OLD_TO_REGION, build_lookup, load_tiger, to_fips
from etl.schema import CLEAN_SOURCES

SOURCE = {"name": "LBNL Queued Up", "version": "2026 edition, queues through 2025",
          "url": "https://eta-publications.lbl.gov/sites/default/files/2026-05/lbnl_ix_queue_data_file_thru2025.xlsx"}
RAW = "lbnl/lbnl_ix_queue_data_file_thru2025.xlsx"
NOTES = ["Queue MW columns and queue_active_count are 0 for counties with no matching queue "
         "entries. Queue age is measured to 2025-12-31.",
         "queue_median_age_years and queue_withdrawal_rate are null when their sample is under 3 "
         "projects, so one stale application can't decide a gate.",
         "queue_operational_mw_5y also counts operational projects with no q_year that came "
         "online in 2021 or later. That raised counties with operational MW from 339 to 353 "
         "and the total from 65.7 GW to 72.0 GW.",
         "Queue rows for old Connecticut counties are summed into the planning region that "
         "holds most of the county, so two regions show no queue activity."]

AS_OF = pd.Timestamp("2025-12-31")  # the file covers queues through the end of 2025
MIN_SAMPLE = 3  # fewer projects than this and the median age or withdrawal rate is noise
UNMATCHED = []  # (state, county, rows) for queue entries that could not be placed in a county


def fetch(raw_dir):
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)


def build(raw_dir):
    q = pd.read_excel(Path(raw_dir) / RAW, sheet_name="03. Complete Queue Data", header=1)
    tiger = load_tiger(raw_dir)
    lookup = build_lookup(tiger)

    q["fips"] = q.fips_code.map(lambda v: f"{int(v):05d}", na_action="ignore").replace(CT_OLD_TO_REGION)
    # Fall back to the county name when the code is blank or retired (Shannon County, SD).
    by_name = ~q.fips.isin(set(tiger.GEOID)) & q.county.notna()
    q.loc[by_name, "fips"] = [to_fips(c, s, lookup) for c, s in zip(q.county[by_name], q.state[by_name])]
    known = q.fips.isin(set(tiger.GEOID))
    in_scope = q.state.isin(set(tiger.STUSPS))
    UNMATCHED[:] = (q[~known & in_scope].groupby(["state", "county"], dropna=False).size()
                    .reset_index().itertuples(index=False, name=None))
    q = q[known].assign(mw_1=q.mw_1.clip(lower=0))  # a few source rows carry negative MW

    active = q[q.q_status == "active"]
    clean = active[active.type_clean.map(lambda t: set(str(t).lower().split("+")) <= CLEAN_SOURCES)]
    recent = q[q.q_year >= 2019]
    counts = recent.groupby(["fips", "q_status"]).size().unstack(fill_value=0)
    resolved = counts.reindex(columns=["withdrawn", "active", "operational"], fill_value=0)

    out = pd.DataFrame({"fips": tiger.GEOID}).set_index("fips")
    out["queue_active_mw_total"] = active.groupby("fips").mw_1.sum()
    out["queue_active_mw_clean"] = clean.groupby("fips").mw_1.sum()
    # 236 operational projects have no q_year. Count those that came online in 2021 or later.
    online = pd.to_datetime(q.on_date, errors="coerce") >= "2021-01-01"
    delivered = q[(q.q_status == "operational") & ((q.q_year >= 2019) | (q.q_year.isna() & online))]
    out["queue_operational_mw_5y"] = delivered.groupby("fips").mw_1.sum()
    out["queue_active_count"] = active.groupby("fips").size()
    out = out.fillna(0.0)
    age_years = ((AS_OF - active.q_date).dt.days / 365.25).groupby(active.fips)
    out["queue_median_age_years"] = age_years.median().where(age_years.count() >= MIN_SAMPLE)
    total = resolved.sum(axis=1)
    out["queue_withdrawal_rate"] = (resolved.withdrawn / total).where(total >= MIN_SAMPLE)
    return out.reset_index()
