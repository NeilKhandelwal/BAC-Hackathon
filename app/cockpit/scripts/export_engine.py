"""Export the real county feature table into the React cockpit contract.

The TypeScript fixture builder owns the display metadata and county geometry.
This script uses that generated contract as a template, replaces every county
value with the corresponding value from the Python engine's feature table, and
marks the result as a real engine snapshot.

Run from app/cockpit with: npm run data:engine
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]
COCKPIT_DATA = ROOT / "app" / "cockpit" / "public" / "data"
TEMPLATE = COCKPIT_DATA / "fixture.json"
FEATURES = ROOT / "data" / "processed" / "county_features.parquet"
MANIFEST = ROOT / "data" / "processed" / "county_features.manifest.json"
OUTPUT = COCKPIT_DATA / "engine-export.json"


def json_number(value):
    """Return a JSON-safe number or None while preserving integer columns."""
    if pd.isna(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    value = float(value)
    return value if math.isfinite(value) else None


def main() -> None:
    if not TEMPLATE.exists():
        raise SystemExit(f"{TEMPLATE} is missing; run npm run data:fixture first")

    data = json.loads(TEMPLATE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    frame = pd.read_parquet(FEATURES)
    frame["fips"] = frame["fips"].astype(str).str.zfill(5)

    if frame["fips"].duplicated().any():
        duplicates = sorted(frame.loc[frame["fips"].duplicated(), "fips"].unique())
        raise SystemExit(f"feature table has duplicate FIPS values: {', '.join(duplicates[:10])}")

    expected = list(data["counties"]["fips"])
    actual = set(frame["fips"])
    missing_counties = sorted(set(expected) - actual)
    extra_counties = sorted(actual - set(expected))
    if missing_counties or extra_counties:
        raise SystemExit(
            "feature table and map county identities differ "
            f"(missing={missing_counties[:10]}, extra={extra_counties[:10]})"
        )

    columns = list(data["values"])
    missing_columns = sorted(set(columns) - set(frame.columns))
    if missing_columns:
        raise SystemExit(f"feature table lacks exported columns: {', '.join(missing_columns)}")

    aligned = frame.set_index("fips").loc[expected]
    data["counties"]["name"] = aligned["county_name"].astype(str).tolist()
    data["counties"]["state"] = aligned["state"].astype(str).tolist()
    data["values"] = {
        column: [json_number(value) for value in aligned[column].tolist()]
        for column in columns
    }
    data["meta"].update(
        source="engine",
        synthetic=False,
        label="Real county values exported from the Python engine feature table.",
        generatedAt=manifest["built_at"],
        notes=[
            "Static demo snapshot of data/processed/county_features.parquet.",
            "Regenerate this file after feature data, pillar semantics, gates, or presets change.",
            "Missing values retain the engine null policy: they are ignored in pillar means and never fail gates.",
        ],
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(data, separators=(",", ":"), allow_nan=False))
    print(
        f"engine export: {len(expected)} counties, {len(columns)} value columns, "
        f"{len(data['presets'])} presets -> {OUTPUT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
