"""LBNL queue measures that score energy/carbon, beside the legacy queue columns kept for traceability.

queue_active_mw_clean_excl_storage and queue_operational_mw_online_5y are the scored queue columns
in engine/pillars.yaml. queue_active_mw_clean and queue_operational_mw_5y, from
etl/adapters/lbnl_queue.py, stay in the table as legacy context and are no longer scored.

County placement copies etl/adapters/lbnl_queue.py exactly (fips_code, old Connecticut counties
to regions, name fallback, negative MW clipped to 0), so both modules see the same projects.
"""
from pathlib import Path

import pandas as pd

from etl.adapters import lbnl_queue
from etl.fips import CT_OLD_TO_REGION, build_lookup, load_tiger, to_fips

SOURCE = {**lbnl_queue.SOURCE, "name": "LBNL Queued Up (scored clean-generation and delivered-capacity measures)",
          "observation_period": "queue snapshot 2025-12-31; online window 2021-01-01 to 2025-12-31",
          "license": "Public; cite Lawrence Berkeley National Laboratory, Queued Up 2026 edition",
          "resolution": "county"}
RAW = lbnl_queue.RAW
NOTES = ["queue_active_mw_clean_excl_storage (scored) counts only identifiable clean-generation capacity "
         "in active projects: solar, wind, offshore wind, hydro, geothermal, and nuclear components. "
         "Each component's separately reported MW counts once (mw_1, mw_2, mw_3 for type_1, type_2, "
         "type_3). A component with no reported MW adds 0, so the measure is conservative: 233 "
         "Solar+Battery rows list only battery capacity and add nothing. A clean component of a gas or "
         "other hybrid counts when its MW is reported. Storage is excluded: it can help integrate "
         "renewables, but it isn't clean generation, because its emissions depend on what charges it.",
         "queue_active_mw_clean (legacy, not scored) counts mw_1 of every active project whose "
         "components are all in etl/schema.py CLEAN_SOURCES, which includes battery and other storage.",
         "queue_active_mw_storage_standalone (not scored) is mw_1 of active projects whose every "
         "component is storage: Battery, Pumped Storage, Storage, or Other Storage.",
         "queue_operational_mw_online_5y (scored) counts operational projects dated to 2021-2025 by "
         "their actual online date (on_date), or by their proposed online date (prop_date) only when "
         "on_date is blank. queue_operational_online_date_fallback_share is the share of each "
         "county's counted projects dated by prop_date. The fallback is substantial where LBNL lacks on_date: "
         "100% of operational ISO-NE projects and 82% in the West. The measure is evidence that the "
         "queue delivers, not proof of capacity available to a new data center.",
         "queue_operational_mw_5y (legacy, not scored) counts operational projects that entered the "
         "queue in 2019 or later (q_year), which measures queue entry rather than delivery."]
CLEAN_GEN = {"Solar", "Wind", "Offshore Wind", "Hydro", "Geothermal", "Nuclear"}
STORAGE = {"Battery", "Pumped Storage", "Storage", "Other Storage"}
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
    """Sum of each clean-generation component's reported MW, counted once; 0 where none is reported."""
    out = pd.Series(0.0, index=q.index)
    for i in (1, 2, 3):
        mw = q[f"mw_{i}"]
        out += mw.where(q[f"type_{i}"].isin(CLEAN_GEN) & mw.notna() & (mw > 0), 0.0)
    return out


def is_standalone_storage(type_clean):
    """True when every '+' component of type_clean is storage, such as Battery+Other Storage."""
    return type_clean.map(lambda t: isinstance(t, str) and set(t.split("+")) <= STORAGE)


def build(raw_dir):
    q, tiger = placed_queue(raw_dir)
    active = q[q.q_status == "active"]
    out = pd.DataFrame({"fips": tiger.GEOID}).set_index("fips")
    out["queue_active_mw_clean_excl_storage"] = clean_generation_mw(active).groupby(active.fips).sum()
    storage = active[is_standalone_storage(active.type_clean)]
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
