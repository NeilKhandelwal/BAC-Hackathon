"""FEMA NRI context: overall ratings, social vulnerability, resilience, and per-hazard physical
frequency and expected-loss scores. Reads the same raw file as etl/adapters/nri.py and leaves
its nri_<hazard>_score and nri_<hazard>_risks columns alone."""
from pathlib import Path

import pandas as pd

from etl.adapters import nri

SOURCE = {**nri.SOURCE, "name": "FEMA NRI (context fields)",
          "observation_period": "hazard-specific periods of record; see the NRI hazard info table",
          "license": "Public domain (FEMA)", "resolution": "county (CT planning regions)"}
RAW = nri.RAW
NOTES = ["nri_<hazard>_annual_freq is NRI's annualized frequency (_AFREQ), the physical-hazard "
         "measure: events per year, drought in days per year, wildfire as an annual probability. "
         "nri_<hazard>_eal_score (_EALS) is the expected-annual-loss percentile, which scales with "
         "exposed value. Neither replaces the scored nri_<hazard>_score.",
         "nri_hurricane_not_applicable and nri_coastal_flood_not_applicable are true where NRI rates "
         "the hazard 'Not Applicable' (_RISKR). Their frequency and EAL score are 0 there, the same "
         "rule nri.py uses for scores."]
HAZARDS = {"DRGT": "drought", "HWAV": "heat_wave", "WFIR": "wildfire", "HRCN": "hurricane",
           "CFLD": "coastal_flood", "IFLD": "inland_flood", "TRND": "tornado", "WNTW": "winter"}


def fetch(raw_dir):
    nri.fetch(raw_dir)


def build(raw_dir):
    d = pd.read_csv(Path(raw_dir) / RAW, dtype={"STCOFIPS": str}, low_memory=False)
    out = pd.DataFrame({"fips": d.STCOFIPS,
                        "nri_risk_rating": d.RISK_RATNG.astype("string"),
                        "nri_eal_score": d.EAL_SCORE.astype("float64"),
                        "nri_sovi_score": d.SOVI_SCORE.astype("float64"),
                        "nri_resilience_score": d.RESL_SCORE.astype("float64")})
    for code, h in HAZARDS.items():
        not_applicable = d[f"{code}_RISKR"] == "Not Applicable"
        out[f"nri_{h}_annual_freq"] = d[f"{code}_AFREQ"].mask(not_applicable, 0.0).astype("float64")
        out[f"nri_{h}_eal_score"] = d[f"{code}_EALS"].mask(not_applicable, 0.0).astype("float64")
        if code in ("HRCN", "CFLD"):
            out[f"nri_{h}_not_applicable"] = not_applicable.astype("boolean")
    return out
