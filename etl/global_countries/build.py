"""Build data/processed/global_country_features.parquet and its manifest.

Usage: python -m etl.global_countries.build
One row per country, keyed by ISO3. Nulls stay null.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from etl.global_countries import sources as s

OUT = Path("data/processed/global_country_features.parquet")


def build():
    base = s.countries()
    wb, wb_years = s.worldbank()
    iso2_to_iso3 = dict(zip(base["iso2"], base["iso3"]))
    pdb = s.peeringdb(iso2_to_iso3)
    df = base.drop(columns="iso2")
    for part in (s.owid_energy(), s.aqueduct(), s.inform(), s.cckp(), pdb, wb):
        df = df.merge(part, on="iso3", how="left", validate="one_to_one")
    # PeeringDB is a global registry, so a country with no listed facility has a real count of zero.
    for c in ("peeringdb_facility_count", "peeringdb_ixp_count"):
        df[c] = df[c].fillna(0).astype(int)
    assert df["iso3"].is_unique and df["iso3"].str.len().eq(3).all()
    return df.sort_values("iso3").reset_index(drop=True), wb_years


def manifest(df, wb_years):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    yr = df["energy_data_year"].dropna().astype(int)
    src = [
        ("World Bank country list", "API v2, regions as published", s.WB_COUNTRIES_URL),
        ("Our World in Data energy dataset (republishes Ember and Energy Institute)",
         f"latest year with carbon intensity per country, {yr.min()}-{yr.max()}, mode {yr.mode().iloc[0]}", s.OWID_URL),
        ("WRI Aqueduct 4.0 country rankings", "2023-07-05 release; baseline and 2050 business as usual, industrial weight",
         s.AQUEDUCT_URL),
        ("EU JRC INFORM Risk Index", "INFORM Risk 2026 v0.7.2, released 2026-03-31", s.INFORM_URL),
        ("World Bank Climate Change Knowledge Portal", "CMIP6 0.25 degree ensemble median, 1995-2014 and 2040-2059",
         s.CCKP_URL.split("{var}")[0]),
        ("PeeringDB", f"live API, fetched {now[:10]}", "https://www.peeringdb.com/api/"),
    ] + [(f"World Bank API {code}", f"most recent non-empty value, {wb_years[name]}",
          s.WB_URL.split("?")[0].format(code=code)) for code, (name, _) in s.WB_INDICATORS.items()]
    return {
        "built_at": now,
        "rows": len(df),
        "sources": [{"name": n, "version": v, "url": u, "fetched_at": now} for n, v, u in src],
        "columns_present": list(df.columns),
        "columns_missing": [],
        "null_counts": {c: int(n) for c, n in df.isna().sum().items()},
        "notes": [
            "Rows are World Bank economies minus aggregates and 22 territories or special administrative regions "
            "(including Hong Kong, Macao, Puerto Rico, Greenland), plus Taiwan, which the World Bank omits. "
            "Taiwan has null World Bank columns.",
            "region is the World Bank region. Taiwan is assigned East Asia & Pacific.",
            "grid_co2_g_kwh is lifecycle gCO2e per kWh of generation as published by OWID. It is not comparable "
            "to the US table's grid_co2_lb_mwh, which is eGRID combustion output emission rate.",
            "water_stress_bws and water_stress_2050 are Aqueduct 0-5 scores, the same scale as the US column.",
            "PeeringDB counts are self-reported registry entries with status ok. Zero means none listed, not unknown.",
            "No open, current, global industrial electricity price exists. The cost pillar is omitted.",
            "No power reliability indicator: the World Bank Enterprise Survey outage series IC.ELC.OUTG returns "
            "'indicator not found' from the API, and Doing Business ended in 2020.",
            "gdp_per_capita_usd is carried in the table but not scored. See docs/global.md.",
        ],
    }


def main():
    df, wb_years = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    m = manifest(df, wb_years)
    OUT.with_name(OUT.stem + ".manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(f"{len(df)} rows, {len(df.columns)} columns -> {OUT}")
    print(pd.Series(m["null_counts"]).to_string())


if __name__ == "__main__":
    main()
