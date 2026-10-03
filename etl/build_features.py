"""Build data/processed/county_features.parquet and its manifest. Contract: docs/schema.md.

Usage: python -m etl.build_features [--no-fetch]

Each adapter in etl/adapters/ exposes SOURCE, RAW, fetch(raw_dir), and build(raw_dir), where
build returns a DataFrame keyed by fips with schema column names only. A failing adapter is
reported, recorded in the manifest, and its columns stay null. The exit code is then 1.
An adapter marked OPTIONAL whose input file is absent only warns.
"""
import argparse
import importlib
import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from etl.schema import CORE, STRETCH

RAW_DIR = Path("data/raw")
OUT_DIR = Path("data/processed")
ADAPTERS = ["tiger_acs", "nri", "cmra", "lbnl_queue", "fcc_fiber", "egrid", "drought_monitor",
            "fractracker", "air_nonattainment", "state_tables", "nrel_wind"]  # tiger_acs must be first: it defines the rows


def _mtime(path):
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(timespec="seconds")


def build(fetch=True):
    table, sources, joins, errors, notes, unmatched, failed = None, [], {}, {}, [], [], []
    for name in ADAPTERS:
        try:
            mod = importlib.import_module(f"etl.adapters.{name}")
            if fetch:
                mod.fetch(RAW_DIR)
            df = mod.build(RAW_DIR)
            unknown = set(df.columns) - set(CORE) - set(STRETCH)
            if unknown:
                raise ValueError(f"columns not in docs/schema.md: {sorted(unknown)}")
            if df.fips.duplicated().any():
                raise ValueError("duplicate fips")
            overlap = set(df.columns) & set(table.columns if table is not None else []) - {"fips"}
            if overlap:
                raise ValueError(f"repeats columns from an earlier adapter: {sorted(overlap)}")
        except Exception as exc:
            if table is None:
                raise
            errors[name] = f"{type(exc).__name__}: {exc}"
            if isinstance(exc, FileNotFoundError) and getattr(mod, "OPTIONAL", False):
                print(f"WARNING: {name} skipped, input not there yet: {exc}", file=sys.stderr)
                continue
            failed.append(name)
            traceback.print_exc()
            print(f"ERROR: adapter {name} failed; its columns stay null", file=sys.stderr)
            continue
        if table is None:
            table = df
        else:
            in_scope = df[df.fips.str[:2].isin(set(table.state_fips))]
            joins[name] = {
                "rows": len(df),
                "fips_not_in_table": sorted(set(in_scope.fips) - set(table.fips)),
                "counties_without_data": int((~table.fips.isin(df.fips)).sum()),
            }
            table = table.merge(df, on="fips", how="left", validate="one_to_one")
        sources.append({**mod.SOURCE, "fetched_at": _mtime(RAW_DIR / mod.RAW)})
        notes += getattr(mod, "NOTES", [])
        unmatched += [(name, *row) for row in getattr(mod, "UNMATCHED", [])]

    if {"hdd_hist", "pop_density_per_sqkm"} <= set(table.columns):
        table["heat_sink_score"] = table.hdd_hist * np.log1p(table.pop_density_per_sqkm)

    for column, dtype in CORE.items():
        if column not in table:
            table[column] = pd.Series(index=table.index, dtype=dtype)
        table[column] = table[column].astype(dtype)
    stretch = [c for c in STRETCH if c in table]
    table = table[[*CORE, *stretch]].sort_values("fips").reset_index(drop=True)

    empty = [c for c in table.columns if table[c].isna().all()]
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": len(table),
        "sources": sources,
        "columns_present": [c for c in table.columns if c not in empty],
        "columns_missing": empty + [c for c in STRETCH if c not in table],
        "null_counts": {c: int(n) for c, n in table.isna().sum().items() if 0 < n < len(table)},
        "notes": notes,
        "joins": joins,
        "errors": errors,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Name joins that failed, logged rather than dropped silently.
    unmatched = pd.DataFrame(unmatched, columns=["source", "state", "county", "rows"])
    unmatched.to_csv(OUT_DIR / "unmatched_names.csv", index=False)
    manifest["unmatched_name_rows"] = {k: int(v) for k, v in unmatched.groupby("source").rows.sum().items()}
    table.to_parquet(OUT_DIR / "county_features.parquet", index=False)
    (OUT_DIR / "county_features.manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return table, manifest, failed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-fetch", action="store_true", help="use data/raw as is")
    table, manifest, failed = build(fetch=not parser.parse_args().no_fetch)
    print(f"rows: {manifest['rows']}")
    print(f"columns present: {len(manifest['columns_present'])}, missing: {manifest['columns_missing']}")
    for name, j in manifest["joins"].items():
        print(f"{name}: {j['rows']} rows, {len(j['fips_not_in_table'])} unmatched fips, "
              f"{j['counties_without_data']} counties without data")
    if failed:
        print(f"FAILED ADAPTERS: {failed}", file=sys.stderr)
        sys.exit(1)
