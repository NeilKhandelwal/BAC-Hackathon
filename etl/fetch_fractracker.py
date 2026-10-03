"""Fetch FracTracker Alliance's US Data Centers Tracker layers to CSV.

Source: https://www.fractracker.org/data-centers (public ArcGIS feature services).
License: free for non-commercial use with credit to FracTracker Alliance.

Writes to data/raw/fractracker/: ft_all.csv (facilities), ft_wins.csv
("Victories" layer), ft_moratoria.csv (moratoria and zoning restrictions).

Usage: python etl/fetch_fractracker.py
"""
import csv
import json
import urllib.parse
import urllib.request
from pathlib import Path

B = "https://services.arcgis.com/jDGuO8tYggdCCnUJ/arcgis/rest/services"
OUT = Path("data/raw/fractracker")


def q(url, geom=False):
    out, off = [], 0
    while True:
        p = dict(where="1=1", outFields="*", returnGeometry=str(geom).lower(), f="json",
                 resultOffset=off, resultRecordCount=1000)
        d = json.load(urllib.request.urlopen(url + "/query?" + urllib.parse.urlencode(p), timeout=60))
        feats = d.get("features", [])
        out += [f["attributes"] for f in feats]
        if not d.get("exceededTransferLimit") or not feats:
            break
        off += len(feats)
    return out


def save(rows, name):
    OUT.mkdir(parents=True, exist_ok=True)
    keys = [k for k in rows[0].keys() if k not in ("Shape__Area", "Shape__Length")]
    with (OUT / name).open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(name, len(rows))


if __name__ == "__main__":
    save(q(B + "/data_centers_v4_agol_all/FeatureServer/0"), "ft_all.csv")
    save(q(B + "/data_centers_wins_v2/FeatureServer/0"), "ft_wins.csv")
    m = []
    for layer in range(4):
        m += q(B + f"/DataCenterMoratoriums/FeatureServer/{layer}")
    save(m, "ft_moratoria.csv")
