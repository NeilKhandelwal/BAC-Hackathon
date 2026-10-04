"""Alternative, non-scored LBNL queue measures beside the scored queue columns.

County placement copies etl/adapters/lbnl_queue.py exactly (fips_code, old Connecticut counties
to regions, name fallback, negative MW clipped to 0), so both modules see the same projects. This
module never changes queue_active_mw_clean, queue_operational_mw_5y, or any queue gate input.
"""
from pathlib import Path

import pandas as pd

from etl.adapters import lbnl_queue
from etl.fips import CT_OLD_TO_REGION, build_lookup, load_tiger, to_fips

SOURCE = {**lbnl_queue.SOURCE, "name": "LBNL Queued Up (alternative queue measures)",
          "observation_period": "queue snapshot 2025-12-31; online window 2021-01-01 to 2025-12-31",
          "license": "Public; cite Lawrence Berkeley National Laboratory, Queued Up 2026 edition",
          "resolution": "county"}
RAW = lbnl_queue.RAW
NOTES = ["queue_active_mw_clean_excl_storage differs from queue_active_mw_clean in two ways. "
         "Standalone storage (Battery, Pumped Storage) is excluded because it isn't generation. For a "
         "hybrid, only the MW of its first clean-generation component counts (mw_1 when type_1 is "
         "clean generation, else mw_2 or mw_3 when given), so a Battery+Solar row with no mw_2 adds 0. "
         "queue_active_mw_clean counts mw_1 of every active project whose components are all in "
         "etl/schema.py CLEAN_SOURCES, which includes battery and other storage.",
         "queue_active_mw_storage_standalone is mw_1 of active projects whose type_clean is Battery, "
         "Pumped Storage, or Storage.",
         "queue_operational_mw_online_5y keys on completion, not queue entry: operational projects "
         "whose on_date falls in 2021-2025, falling back to prop_date (proposed online date) when "
         "on_date is blank. queue_operational_mw_5y instead counts operational projects with q_year "
         "2019 or later, plus undated-q_year projects online since 2021. on_date is filled for about "
         "99% of operational PJM, CAISO, and MISO rows but 18% in the West and 0% in ISO-NE; "
         "queue_operational_online_date_fallback_share reports how many were dated by prop_date."]
CLEAN_GEN = {"Solar", "Wind", "Offshore Wind", "Hydro", "Geothermal", "Nuclear"}
STORAGE = {"Battery", "Pumped Storage", "Storage"}
WINDOW = (pd.Timestamp("2021-01-01"), lbnl_queue.AS_OF)


def fetch(raw_dir):
    lbnl_queue.fetch(raw_dir)


def placed_queue(raw_dir):
    """Queue rows with fips, placed exactly as lbnl_queue.build places them."""
    q = pd.read_excel(Path(raw_dir) / RAW, sheet_name="03. Complete Queue Data", header=1)
    tiger = load_tiger(raw_dir)
    lookup = build_lookup(tiger)
    q["fips"] = q.fips_code.map(lambda v: f"{int(v):05d}", na_action="ignore").replace(CT_OLD_TO_REGION)
    by_name = ~q.fips.isin(set(tiger.GEOID)) & q.county.notna()
    q.loc[by_name, "fips"] = [to_fips(c, s, lookup) for c, s in zip(q.county[by_name], q.state[by_name])]
    q = q[q.fips.isin(set(tiger.GEOID))]
    for c in ("mw_1", "mw_2", "mw_3"):
        q[c] = pd.to_numeric(q[c], errors="coerce")
    return q.assign(mw_1=q.mw_1.clip(lower=0)), tiger


def clean_generation_mw(q):
    """MW of the first clean-generation component; 0 when that component has no MW."""
    out = pd.Series(0.0, index=q.index)
    done = pd.Series(False, index=q.index)
    for i in (1, 2, 3):
        is_clean = q[f"type_{i}"].isin(CLEAN_GEN) & ~done
        has_mw = is_clean & q[f"mw_{i}"].notna() & (q[f"mw_{i}"] > 0)
        out[has_mw] = q.loc[has_mw, f"mw_{i}"]
        done |= is_clean
    return out


def build(raw_dir):
    q, tiger = placed_queue(raw_dir)
    active = q[q.q_status == "active"]
    out = pd.DataFrame({"fips": tiger.GEOID}).set_index("fips")
    out["queue_active_mw_clean_excl_storage"] = clean_generation_mw(active).groupby(active.fips).sum()
    storage = active[active.type_clean.isin(STORAGE)]
    out["queue_active_mw_storage_standalone"] = storage.groupby("fips").mw_1.sum()
    op = q[q.q_status == "operational"].copy()
    on, prop = pd.to_datetime(op.on_date, errors="coerce"), pd.to_datetime(op.prop_date, errors="coerce")
    op["online"], op["fallback"] = on.fillna(prop), on.isna() & prop.notna()
    w = op[op.online.between(*WINDOW)]
    out["queue_operational_mw_online_5y"] = w.groupby("fips").mw_1.sum()
    out["queue_operational_projects_online_5y"] = w.groupby("fips").size()
    out = out.fillna(0.0)
    out["queue_operational_projects_online_5y"] = out.queue_operational_projects_online_5y.astype("Int64")
    out["queue_operational_online_date_fallback_share"] = w.groupby("fips").fallback.mean().astype("float64")
    return out.reset_index()
