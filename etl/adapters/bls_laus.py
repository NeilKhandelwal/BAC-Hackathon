"""BLS LAUS county unemployment, 2024 annual average and pooled 2022-2024.

Adds context columns beside unemployment_rate_pct_2023 (ERS republication), which stays the
scored field. Rates are percents, 0-100, to match unemployment_rate_pct_2023.
"""
import os
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download

URL = "https://www.bls.gov/lau/laucnty{yy}.xlsx"
YEARS = [2022, 2023, 2024]
SOURCE = {"name": "BLS Local Area Unemployment Statistics", "version": "county annual averages, files reissued 2026-05-19",
          "url": URL.format(yy=24), "observation_period": "2024 annual average; pooled 2022-2024",
          "license": "Public domain (U.S. Bureau of Labor Statistics)", "resolution": "county (CT planning regions)"}
RAW = "bls/laucnty24.xlsx"
NOTES = ["LAUS 2024 is the latest complete year. The 2025 file is an 11-month average because "
         "October 2025 wasn't collected, so it isn't used.",
         "unemployment_rate_pct_3yr_2022_2024 pools counts: 100 x sum(unemployed) / sum(labor "
         "force) over 2022-2024. It's null unless all three years are present.",
         "bls.gov/lau refuses requests without a contact address in the User-Agent. Set "
         "BLS_CONTACT_EMAIL for the first download; cached files need nothing."]


def _headers():
    contact = os.environ.get("BLS_CONTACT_EMAIL")
    if not contact:
        raise RuntimeError("BLS_CONTACT_EMAIL is not set; bls.gov/lau requires a contact address "
                           "in the User-Agent. Set it to download, or place cached files in data/raw/bls/.")
    return {"User-Agent": f"Mozilla/5.0 (research; {contact})"}


def fetch(raw_dir):
    for y in YEARS:
        dest = Path(raw_dir) / f"bls/laucnty{str(y)[2:]}.xlsx"
        if not dest.exists():
            download(URL.format(yy=str(y)[2:]), dest, 1e5, ZIP_MAGIC, headers=_headers())


def read_year(path, year):
    d = pd.read_excel(path, skiprows=1, header=0, dtype={"State FIPS Code": str, "County FIPS Code": str})
    d = d[d["State FIPS Code"].fillna("").str.fullmatch(r"\d{2}")
          & d["County FIPS Code"].fillna("").str.fullmatch(r"\d{3}")]
    if not (d["Year"].astype(str).str[:4] == str(year)).all():
        raise ValueError(f"{path}: rows for a year other than {year}")
    out = pd.DataFrame({"fips": d["State FIPS Code"] + d["County FIPS Code"],
                        "labor_force": pd.to_numeric(d["Labor Force"], errors="coerce"),
                        "unemployed": pd.to_numeric(d["Unemployed"], errors="coerce"),
                        "rate_pct": pd.to_numeric(d["Unemployment Rate (%)"], errors="coerce")})
    if out.fips.duplicated().any():
        raise ValueError(f"{path}: duplicate county rows")
    return out


def build(raw_dir):
    years = {y: read_year(Path(raw_dir) / f"bls/laucnty{str(y)[2:]}.xlsx", y) for y in YEARS}
    cur = years[2024].set_index("fips")
    stack = pd.concat([d.assign(year=y) for y, d in years.items()])
    g = stack.groupby("fips").agg(n=("year", "nunique"), u=("unemployed", "sum"), lf=("labor_force", "sum"))
    pooled = (100 * g.u / g.lf).where(g.n == len(YEARS))
    out = pd.DataFrame({"fips": cur.index})
    out["unemployment_rate_pct_2024"] = cur.rate_pct.values.astype("float64")
    out["unemployment_rate_pct_3yr_2022_2024"] = out.fips.map(pooled).astype("float64")
    out["unemployed_persons_2024"] = cur.unemployed.round().astype("Int64").values
    out["labor_force_2024"] = cur.labor_force.round().astype("Int64").values
    return out
