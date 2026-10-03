"""Census County Business Patterns: manufacturing employment in 2001 and the jobs lost by 2022."""
from pathlib import Path

import pandas as pd

from etl.download import ZIP_MAGIC, download
from etl.fips import CT_OLD_TO_REGION, load_tiger

SOURCE = {"name": "Census County Business Patterns", "version": "2001 and 2022",
          "url": "https://www2.census.gov/programs-surveys/cbp/datasets/2022/cbp22co.zip"}
RAW = "cbp/cbp22co.zip"
URL_2001 = "https://www2.census.gov/programs-surveys/cbp/datasets/2001/cbp01co.zip"
NOTES = ["CBP counts private wage-and-salary jobs in mid-March. It leaves out the self-employed "
         "and government.",
         "CBP 2001 withholds small cells and gives a size class instead. Those cells take the "
         "class midpoint. The open top class (100,000 or more) takes 100,000. 364 of 3,074 "
         "county manufacturing cells in 2001 (12 percent) are imputed this way, mostly in small "
         "counties, so treat mfg_loss_share_emp_2001 there as approximate.",
         "Counties with no manufacturing row in a year have 0 manufacturing jobs that year.",
         "2001 counts for Connecticut's old counties are summed into the planning region that "
         "holds most of the county. Two regions get no 2001 count, so their columns are null.",
         "Broomfield, CO (08014) didn't exist in March 2001, so its columns are null.",
         "mfg_loss_share_emp_2001 has no lower bound. Counties that grew from a small 2001 base "
         "go far below -1, such as Storey County, NV at -19.4. Clip or rank it before modeling."]

# CBP 2001 employment size classes for withheld cells -> class midpoint.
FLAG_MIDPOINT = {"A": 10, "B": 60, "C": 175, "E": 375, "F": 750, "G": 1750, "H": 3750,
                 "I": 7500, "J": 17500, "K": 37500, "L": 75000, "M": 100000}
# 2001 FIPS -> 2022 FIPS for counties that were renamed or merged in between.
FIPS_2001_TO_2022 = {"12025": "12086",  # Dade -> Miami-Dade
                     "46113": "46102",  # Shannon -> Oglala Lakota
                     "51515": "51019",  # Bedford city merged into Bedford County
                     "51560": "51005",  # Clifton Forge merged into Alleghany County
                     "11999": "11001",  # CBP 2001 codes all of DC as unallocated
                     **CT_OLD_TO_REGION}


def fetch(raw_dir):
    download(URL_2001, Path(raw_dir) / "cbp/cbp01co.zip", 1e6, ZIP_MAGIC)
    download(SOURCE["url"], Path(raw_dir) / RAW, 1e6, ZIP_MAGIC)


def _employment(path, flag, midpoints=None):
    """Total and manufacturing employment by FIPS for one CBP year.

    midpoints maps withheld-cell size classes to jobs. Only 2001 uses them. The 2022 flag column
    holds noise flags (G, H, J) that share letters with the size classes, so pass None there.
    """
    d = pd.read_csv(path, dtype=str, usecols=["fipstate", "fipscty", "naics", flag, "emp"])
    d["fips"] = d.fipstate + d.fipscty
    emp = d.emp.astype(float)
    d["emp"] = emp if midpoints is None else emp.mask(emp.eq(0) & d[flag].isin(midpoints), d[flag].map(midpoints))
    total = d[d.naics == "------"].set_index("fips").emp
    mfg = d[d.naics == "31----"].set_index("fips").emp.reindex(total.index, fill_value=0.0)
    return pd.DataFrame({"total": total, "mfg": mfg})


def build(raw_dir):
    raw = Path(raw_dir) / "cbp"
    y01 = _employment(raw / "cbp01co.zip", "empflag", FLAG_MIDPOINT)
    y01 = y01.groupby(lambda f: FIPS_2001_TO_2022.get(f, f)).sum()
    y22 = _employment(raw / "cbp22co.zip", "emp_nf")

    out = pd.DataFrame({"fips": load_tiger(raw_dir).GEOID}).set_index("fips")
    y01, y22 = y01.reindex(out.index), y22.reindex(out.index)
    out["mfg_emp_share_2001"] = y01.mfg / y01.total
    out["mfg_loss_share_emp_2001"] = (y01.mfg - y22.mfg) / y01.total
    return out.reset_index()
