"""Append columns from named adapters to the frozen county table, leaving every existing column as is.

Usage: python -m etl.append_columns ADAPTER [ADAPTER ...] [--no-fetch]

The committed table is a frozen artifact (docs/schema.md, "Frozen artifacts and reproducibility"). A
full rebuild needs every raw source and can shift small spatial values, so new columns are added
this way instead. Each adapter must produce only new schema columns. The manifest gains the
adapters' sources, notes, and join stats, recomputed present, missing, and null-count lists, and a
"patches" entry. The quality report is recomputed. A fresh `python -m etl.build_features` run
produces the same new columns, because the adapters are also registered there.
"""
import argparse
import importlib
import json
from datetime import datetime, timezone

import pandas as pd

from etl import quality
from etl.build_features import OUT_DIR, RAW_DIR, _mtime
from etl.schema import CORE, STRETCH

TABLE = OUT_DIR / "county_features.parquet"
MANIFEST = OUT_DIR / "county_features.manifest.json"


def append(names, fetch=True):
    table = pd.read_parquet(TABLE)
    frozen_dtypes = table.dtypes  # merging on fips can change its dtype; existing columns keep theirs
    manifest = json.loads(MANIFEST.read_text())
    added = []
    for name in names:
        mod = importlib.import_module(f"etl.adapters.{name}")
        if fetch:
            mod.fetch(RAW_DIR)
        df = mod.build(RAW_DIR)
        new = [c for c in df.columns if c != "fips"]
        unknown = set(new) - set(CORE) - set(STRETCH)
        if unknown:
            raise ValueError(f"{name}: columns not in docs/schema.md: {sorted(unknown)}")
        clash = set(new) & set(table.columns)
        if clash:
            raise ValueError(f"{name}: columns already in the frozen table: {sorted(clash)}")
        if df.fips.duplicated().any():
            raise ValueError(f"{name}: duplicate fips")
        in_scope = df[df.fips.str[:2].isin(set(table.state_fips))]
        manifest.setdefault("joins", {})[name] = {
            "rows": len(df),
            "fips_not_in_table": sorted(set(in_scope.fips) - set(table.fips)),
            "counties_without_data": int((~table.fips.isin(df.fips)).sum()),
        }
        table = table.merge(df, on="fips", how="left", validate="one_to_one")
        for c in new:
            table[c] = table[c].astype(STRETCH.get(c, CORE.get(c)))
        manifest["sources"].append({**mod.SOURCE, "adapter": name, "fetched_at": _mtime(RAW_DIR / mod.RAW)})
        manifest["notes"] += getattr(mod, "NOTES", [])
        added += new

    stretch = [c for c in STRETCH if c in table]
    table = table[[*CORE, *stretch]].sort_values("fips").reset_index(drop=True)
    for c, dtype in frozen_dtypes.items():
        table[c] = table[c].astype(dtype)
    empty = [c for c in table.columns if table[c].isna().all()]
    manifest["columns_present"] = [c for c in table.columns if c not in empty]
    manifest["columns_missing"] = empty + [c for c in STRETCH if c not in table]
    manifest["null_counts"] = {c: int(n) for c, n in table.isna().sum().items() if 0 < n < len(table)}
    manifest.setdefault("patches", []).append({
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "adapters": list(names),
        "columns_added": added, "rule": "frozen-artifact policy: existing columns unchanged"})
    table.to_parquet(TABLE, index=False)
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    quality.write_report(table, manifest, OUT_DIR / "county_features_quality_report.json")
    return table, manifest, added


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("adapters", nargs="+")
    parser.add_argument("--no-fetch", action="store_true", help="use data/raw as is")
    args = parser.parse_args()
    table, manifest, added = append(args.adapters, fetch=not args.no_fetch)
    print(f"added {added}; rows {len(table)}; columns {len(table.columns)}")
