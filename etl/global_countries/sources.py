"""Fetchers for the country table. One function per source, each returning a frame keyed by iso3.

Raw downloads are cached under data/raw/global/ by etl.download. Every source is open and keyless.
"""
import json
import zipfile
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download

RAW = Path("data/raw/global")

OWID_URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
AQUEDUCT_URL = "https://files.wri.org/aqueduct/aqueduct-4-0-country-rankings.zip"
INFORM_URL = "https://drmkc.jrc.ec.europa.eu/inform-index/Portals/0/InfoRM/2026/INFORM_Risk_2026_v072.xlsx"
CCKP_URL = ("https://cckpapi.worldbank.org/cckp/v1/cmip6-x0.25_climatology_{var}_climatology_annual_"
            "{period}_median_{scenario}_ensemble_all_mean/all_countries?_format=json")
PEERINGDB_URL = "https://www.peeringdb.com/api/{obj}?fields=country,status"
WB_COUNTRIES_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
WB_URL = "https://api.worldbank.org/v2/country/all/indicator/{code}?format=json&per_page=20000&mrnev=1{source}"

# World Bank economies that are territories or special administrative regions, not countries.
TERRITORIES = {
    "ABW", "ASM", "BMU", "CHI", "CUW", "CYM", "FRO", "GIB", "GRL", "GUM", "HKG", "IMN", "MAC",
    "MAF", "MNP", "NCL", "PRI", "PYF", "SXM", "TCA", "VGB", "VIR",
}


def _json(url, name):
    return json.loads(download(url, RAW / name, min_bytes=100).read_text())


def countries():
    """World Bank economies minus aggregates and territories, plus Taiwan, which the World Bank omits."""
    rows = [c for c in _json(WB_COUNTRIES_URL, "wb_countries.json")[1] if c["region"]["value"] != "Aggregates"]
    df = pd.DataFrame({
        "iso3": [c["id"] for c in rows],
        "iso2": [c["iso2Code"] for c in rows],
        "country": [c["name"] for c in rows],
        "region": [c["region"]["value"].strip() for c in rows],
    })
    df = df[~df["iso3"].isin(TERRITORIES)]
    twn = pd.DataFrame([{"iso3": "TWN", "iso2": "TW", "country": "Taiwan", "region": "East Asia & Pacific"}])
    return pd.concat([df, twn], ignore_index=True)


def owid_energy():
    """Latest year with a carbon intensity value per country; the other columns come from that same year."""
    df = pd.read_csv(download(OWID_URL, RAW / "owid-energy-data.csv", min_bytes=1_000_000))
    df = df[df["iso_code"].str.len() == 3].dropna(subset=["carbon_intensity_elec"])
    df = df.sort_values("year").groupby("iso_code").tail(1)
    return df.rename(columns={
        "iso_code": "iso3",
        "year": "energy_data_year",
        "carbon_intensity_elec": "grid_co2_g_kwh",
        "renewables_share_elec": "renewable_share_elec_pct",
        "low_carbon_share_elec": "low_carbon_share_elec_pct",
        "electricity_generation": "electricity_generation_twh",
    })[["iso3", "energy_data_year", "grid_co2_g_kwh", "renewable_share_elec_pct",
        "low_carbon_share_elec_pct", "electricity_generation_twh"]]


def aqueduct():
    """Baseline water stress and the 2050 business-as-usual projection, industrial weighting, 0-5 score."""
    z = download(AQUEDUCT_URL, RAW / "aqueduct-4-0-country-rankings.zip", min_bytes=1_000_000, magic=ZIP_MAGIC)
    xlsx = "Aqueduct40_rankings_download_Y2023M07D05/Aqueduct40_rankings_download_Y2023M07D05.xlsx"
    with zipfile.ZipFile(z) as zf, zf.open(xlsx) as fh:
        sheets = pd.read_excel(fh, sheet_name=["country_baseline", "country_future"])
    b, f = sheets["country_baseline"], sheets["country_future"]
    b = b[(b.indicator_name == "bws") & (b.weight == "Ind")].set_index("gid_0")["score"]
    f = f[(f.indicator_name == "bws") & (f.weight == "Ind") & (f.year == 2050) & (f.scenario == "bau")]
    f = f.set_index("gid_0")["score"]
    out = pd.DataFrame({"water_stress_bws": b, "water_stress_2050": f})
    return out.where(out >= 0).rename_axis("iso3").reset_index()  # negative scores are no-data codes


def inform():
    """INFORM Risk 2026 natural hazard exposure components, each 0-10."""
    # The JRC server serves an HTML challenge to the full Chrome user agent in etl.download, not to a short one.
    path = download(INFORM_URL, RAW / "INFORM_Risk_2026_v072.xlsx", min_bytes=1_000_000, magic=ZIP_MAGIC,
                    headers={"User-Agent": "Mozilla/5.0"})
    df = pd.read_excel(path, sheet_name="INFORM Risk 2026 (a-z)", header=1).iloc[1:]  # row 2 holds units
    cols = {"Earthquake": "inform_earthquake", "River Flood": "inform_river_flood", "Tsunami": "inform_tsunami",
            "Tropical Cyclone": "inform_tropical_cyclone", "Coastal flood": "inform_coastal_flood",
            "Drought": "inform_drought"}
    out = df[["ISO3"] + list(cols)].rename(columns={"ISO3": "iso3", **cols})
    for c in cols.values():
        out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.dropna(subset=["iso3"])


def cckp():
    """CMIP6 ensemble medians from the World Bank Climate Change Knowledge Portal.

    cdd65: cooling degree days, base 65F. hd35: days with max temperature above 35C.
    Historical is 1995-2014; mid-century is 2040-2059 under SSP2-4.5 and SSP5-8.5.
    """
    frames = []
    for var in ("cdd65", "hd35"):
        for period, scenario, name in (("1995-2014", "historical", f"{var}_hist"),
                                       ("2040-2059", "ssp245", f"{var}_2050_ssp245"),
                                       ("2040-2059", "ssp585", f"{var}_2050_ssp585")):
            data = _json(CCKP_URL.format(var=var, period=period, scenario=scenario), f"cckp_{name}.json")["data"]
            frames.append(pd.Series({k: next(iter(v.values())) for k, v in data.items()}, name=name, dtype=float))
    return pd.concat(frames, axis=1).rename_axis("iso3").reset_index()


def peeringdb(iso2_to_iso3):
    """Counts of PeeringDB facilities and internet exchanges with status ok, by country."""
    out = {}
    for obj, name in (("fac", "peeringdb_facility_count"), ("ix", "peeringdb_ixp_count")):
        rows = _json(PEERINGDB_URL.format(obj=obj), f"peeringdb_{obj}.json")["data"]
        s = pd.Series([r["country"] for r in rows if r.get("status") == "ok"]).map(iso2_to_iso3)
        out[name] = s.value_counts()
    return pd.DataFrame(out).rename_axis("iso3").reset_index()


WB_INDICATORS = {
    "SP.POP.TOTL": ("population", ""),
    "NY.GDP.PCAP.CD": ("gdp_per_capita_usd", ""),
    "SL.UEM.TOTL.ZS": ("unemployment_rate_pct", ""),
    "IT.NET.BBND.P2": ("broadband_per_100", ""),
    "GOV_WGI_PV.EST": ("wgi_political_stability", "&source=3"),
    "GOV_WGI_RQ.EST": ("wgi_regulatory_quality", "&source=3"),
    "GOV_WGI_RL.EST": ("wgi_rule_of_law", "&source=3"),
}


def worldbank():
    """Most recent non-empty value per country for each indicator. Returns (frame, {column: year range})."""
    frames, years = [], {}
    for code, (name, source) in WB_INDICATORS.items():
        rows = _json(WB_URL.format(code=code, source=source), f"wb_{code}.json")[1]
        # The WGI source labels "Taiwan, China" with iso3 SYR and "Netherlands Antilles" with NLD, both
        # with an empty country id. Keep rows by country id, and take Taiwan by its name.
        rows = [{**r, "countryiso3code": "TWN"} if r["country"]["value"] == "Taiwan, China" else r
                for r in rows if (r["country"]["id"] and r["countryiso3code"]) or r["country"]["value"] == "Taiwan, China"]
        df = pd.DataFrame([(r["countryiso3code"], r["value"], r["date"]) for r in rows if r["value"] is not None],
                          columns=["iso3", name, "year"]).set_index("iso3")
        years[name] = f"{df['year'].min()}-{df['year'].max()}" if df["year"].nunique() > 1 else df["year"].iloc[0]
        frames.append(df[name].astype(float))
    return pd.concat(frames, axis=1).rename_axis("iso3").reset_index(), years
