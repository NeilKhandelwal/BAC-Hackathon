"""USDA ERS Rural-Urban Continuum Codes 2023 and County Typology Codes 2025. Context only."""
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import CT_OLD_TO_REGION

RUCC_URL = "https://www.ers.usda.gov/media/5767/2023-rural-urban-continuum-codes.xlsx"
TYPO_URL = "https://www.ers.usda.gov/media/6173/ers-county-typology-codes-2025-edition.xlsx"
SOURCE = {"name": "USDA ERS Rural-Urban Continuum Codes 2023 and County Typology Codes 2025",
          "version": "RUCC 2023 (January 2024 release); County Typology Codes 2025 edition (April 2025)",
          "url": TYPO_URL,
          "observation_period": "RUCC: OMB July 2023 delineation, 2020 Census population. Typology: "
                                "industry dependence on BEA 2019/2021/2022 average; low employment on "
                                "ACS 2018-2022; population loss on 2000-2010 and 2010-2020 censuses.",
          "license": "Public domain (USDA Economic Research Service)", "resolution": "county"}
RAW = "ers/typology2025.xlsx"
NOTES = ["Rurality and county typology are categorical context, not suitability scores, and say "
         "nothing about community support for data centers. Edition year is not observation year.",
         "Typology code 99 (not available) is null.",
         "ERS Typology 2025 reports the economic and population-loss codes for Connecticut's old "
         "counties and the ACS-based codes for planning regions. Binary flags aren't moved across "
         "geographies, so CT regions have null ers_high_manufacturing_2025, ers_high_mining_2025, "
         "ers_industry_dependence_2025, and ers_population_loss_2025."]
INDUSTRY = {0: "nonspecialized", 1: "farming", 2: "mining", 3: "manufacturing", 4: "government",
            5: "recreation"}


def fetch(raw_dir):
    download(RUCC_URL, Path(raw_dir) / "ers/rucc2023.xlsx", 1e4, ZIP_MAGIC)
    download(TYPO_URL, Path(raw_dir) / RAW, 1e4, ZIP_MAGIC)


def _flag(s):
    v = pd.to_numeric(s, errors="coerce")
    return v.where(v.isin([0, 1])).astype("Int64").astype("boolean")


def build(raw_dir):
    r = pd.read_excel(Path(raw_dir) / "ers/rucc2023.xlsx", sheet_name="Rural-urban Continuum Code 2023",
                      dtype={"FIPS": str})
    rucc = pd.DataFrame({"fips": r.FIPS.str.zfill(5),
                         "rucc_2023": pd.to_numeric(r.RUCC_2023, errors="coerce").astype("Int64"),
                         "rucc_2023_description": r.Description.astype("string")})
    rucc["metro_2023"] = (rucc.rucc_2023 <= 3).astype("boolean").mask(rucc.rucc_2023.isna())
    y = pd.read_excel(Path(raw_dir) / RAW, sheet_name="2025 ERS County Typology Codes", dtype={"FIPStxt": str})
    typo = pd.DataFrame({"fips": y.FIPStxt.str.zfill(5),
                         "ers_high_manufacturing_2025": _flag(y.High_Manufacturing_2025),
                         "ers_high_mining_2025": _flag(y.High_Mining_2025),
                         "ers_low_employment_2025": _flag(y.Low_Employment_2025),
                         "ers_population_loss_2025": _flag(y.Population_Loss_2025),
                         "ers_industry_dependence_2025":
                             pd.to_numeric(y.Industry_Dependence_2025, errors="coerce").map(INDUSTRY).astype("string")})
    for df in (rucc, typo):
        if df.fips.duplicated().any():
            raise ValueError("duplicate FIPS in an ERS file")
    out = rucc.merge(typo, on="fips", how="outer")
    return out[~out.fips.isin(CT_OLD_TO_REGION)].reset_index(drop=True)
