"""BLS QCEW private manufacturing employment and establishments, 2015, 2019, 2024, 2025.

Context columns beside the CBP and BEA manufacturing fields, which stay as they are.
"""
from pathlib import Path

import pandas as pd

from etl.download import download
from etl.fips import CT_OLD_TO_REGION

URL = "https://data.bls.gov/cew/data/api/{year}/a/industry/{ind}.csv"
YEARS = [2015, 2019, 2024, 2025]
BASE, MID, CURRENT = 2015, 2019, 2024
SOURCE = {"name": "BLS Quarterly Census of Employment and Wages", "version": "annual averages, open-data CSV slices",
          "url": URL.format(year=CURRENT, ind="31_33"),
          "observation_period": "annual averages 2015, 2019, 2024 (current); 2025 levels only (first release)",
          "license": "Public domain (U.S. Bureau of Labor Statistics)", "resolution": "county"}
RAW = "bls/qcew_2024_a_31_33.csv"
NOTES = ["QCEW manufacturing is NAICS 31-33, private ownership (own_code 5), county by sector "
         "(agglvl_code 74). mfg_emp_share_2024 divides by county private total employment "
         "(own_code 5, agglvl_code 71), the same ownership.",
         "Suppressed QCEW cells (disclosure_code N) publish employment as 0; they are null here and "
         "flagged in mfg_emp_suppressed_<year>. Establishment counts are still published for them.",
         "A county with a published private total but no manufacturing row has a confirmed 0.",
         "mfg_emp_pct_change_2015_2024 is a fraction and is null when 2015 employment is 0 or unknown.",
         "2024 is the current QCEW year. 2025 annual data are a first release with about twice the "
         "suppression of 2024, so 2025 appears as levels only.",
         "QCEW 2015 and 2019 key Connecticut by its old counties. Job counts aren't split across "
         "planning regions, so CT 2015 and 2019 levels and every change column are null for CT.",
         "Shannon County, SD (46113) is recoded to Oglala Lakota County (46102) when only the old "
         "code is published."]
RENAMES = {"46113": "46102"}


def fetch(raw_dir):
    for y in YEARS:
        for ind in ("31_33", "10"):
            download(URL.format(year=y, ind=ind), Path(raw_dir) / f"bls/qcew_{y}_a_{ind}.csv", 1e5)


def county_rows(path, own, agglvl):
    """County rows for one ownership and aggregation level. Suppressed employment becomes null."""
    d = pd.read_csv(path, dtype={"area_fips": str, "own_code": str, "agglvl_code": str,
                                 "disclosure_code": str}, low_memory=False)
    x = d[(d.own_code == own) & (d.agglvl_code == agglvl)].copy()
    x = x[x.area_fips.str.fullmatch(r"\d{5}") & ~x.area_fips.str.endswith(("000", "999"))]
    for old, new in RENAMES.items():
        if not (x.area_fips == new).any():
            x.loc[x.area_fips == old, "area_fips"] = new
    x = x[~x.area_fips.isin(RENAMES)]
    if x.area_fips.duplicated().any():
        raise ValueError(f"{path}: duplicate county rows")
    x["suppressed"] = x.disclosure_code.fillna("").str.strip().eq("N")
    x["emp"] = pd.to_numeric(x.annual_avg_emplvl, errors="coerce").astype("Float64").mask(x.suppressed)
    x["estabs"] = pd.to_numeric(x.annual_avg_estabs, errors="coerce").astype("Int64")
    return x.set_index("area_fips")[["emp", "estabs", "suppressed"]]


def build(raw_dir):
    raw = Path(raw_dir) / "bls"
    out = None
    totals = {}
    for y in YEARS:
        m = county_rows(raw / f"qcew_{y}_a_31_33.csv", "5", "74")
        totals[y] = county_rows(raw / f"qcew_{y}_a_10.csv", "5", "71")
        fips = m.index.union(totals[y].index)
        m = m.reindex(fips)
        # Published county, no manufacturing row: confirmed zero, not unknown.
        zero = fips.isin(totals[y].index) & ~fips.isin(m.dropna(how="all").index)
        m.loc[zero, ["emp", "estabs"]] = 0
        m.loc[zero, "suppressed"] = False
        y_df = pd.DataFrame({f"mfg_emp_{y}": m.emp.astype("Float64"),
                             f"mfg_estabs_{y}": m.estabs.astype("Int64"),
                             f"mfg_emp_suppressed_{y}": m.suppressed.astype("boolean")})
        out = y_df if out is None else out.join(y_df, how="outer")
    out["private_emp_2024"] = totals[CURRENT].emp.reindex(out.index).astype("Float64")
    b, c = out[f"mfg_emp_{BASE}"], out[f"mfg_emp_{CURRENT}"]
    out["mfg_emp_share_2024"] = (c / out.private_emp_2024).where(out.private_emp_2024 > 0)
    out["mfg_emp_change_2015_2024"] = c - b
    out["mfg_emp_pct_change_2015_2024"] = ((c - b) / b).where(b > 0)
    out["mfg_jobs_lost_2015_2024"] = (b - c).clip(lower=0)
    out["mfg_emp_change_2019_2024"] = c - out[f"mfg_emp_{MID}"]
    for col in out.columns:
        if str(out[col].dtype) == "Float64":
            out[col] = out[col].astype("float64")  # NaN-backed float, like the rest of the table
    out = out[~out.index.isin(CT_OLD_TO_REGION)]  # old CT counties: kept out, see NOTES
    return out.rename_axis("fips").reset_index()
