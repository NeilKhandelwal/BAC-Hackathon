"""FEMA National Risk Index hazard scores."""
from pathlib import Path

import pandas as pd

from etl.arcgis import fetch_csv

SOURCE = {"name": "FEMA NRI", "version": "v1.20",
          "url": "https://services.arcgis.com/XG15cJAlne2vxtgt/arcgis/rest/services/National_Risk_Index_Counties/FeatureServer/0"}
RAW = "nri/nri_counties.csv"
NOTES = ["NRI hazard scores rated 'Not Applicable' are written as 0, not null. "
         "'Insufficient Data' stays null."]

COLUMNS = {
    "RISK": "nri_risk_score", "DRGT": "nri_drought_score", "IFLD": "nri_inland_flood_score",
    "CFLD": "nri_coastal_flood_score", "WFIR": "nri_wildfire_score",
    "HRCN": "nri_hurricane_score", "HWAV": "nri_heat_wave_score", "TRND": "nri_tornado_score",
    "WNTW": "nri_winter_score",
}


def fetch(raw_dir):
    # outFields=* on purpose: the raw file keeps the loss-rate fields in case scoring switches.
    fetch_csv(SOURCE["url"], Path(raw_dir) / RAW)


def build(raw_dir):
    nri = pd.read_csv(Path(raw_dir) / RAW, dtype={"STCOFIPS": str}, low_memory=False)
    out = pd.DataFrame({"fips": nri.STCOFIPS})
    out["nri_risk_score"] = nri.RISK_SCORE
    for hazard, column in COLUMNS.items():
        if hazard == "RISK":
            continue
        # "Not Applicable" means the hazard can't occur there (coastal flooding inland), which is
        # a real zero. "Insufficient Data" stays null.
        out[column] = nri[f"{hazard}_RISKS"].mask(nri[f"{hazard}_RISKR"] == "Not Applicable", 0.0)
    return out
