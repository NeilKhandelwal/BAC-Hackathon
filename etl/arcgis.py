"""Shared pager for ArcGIS feature services (NRI, CMRA, FCC, FracTracker)."""
from pathlib import Path

import pandas as pd
import requests


def query_all(layer_url, where="1=1", out_fields="*", page=1000, timeout=120):
    """Return every row's attributes from a feature layer. No geometry."""
    rows, offset = [], 0
    while True:
        params = dict(where=where, outFields=out_fields, returnGeometry="false", f="json",
                      resultOffset=offset, resultRecordCount=page, orderByFields="OBJECTID")
        r = requests.get(layer_url + "/query", params=params, timeout=timeout)
        r.raise_for_status()
        d = r.json()
        if "error" in d:
            raise RuntimeError(f"{layer_url} at offset {offset}: {d['error']}")
        feats = d.get("features", [])
        rows += [f["attributes"] for f in feats]
        if not feats or not d.get("exceededTransferLimit"):
            return rows
        offset += len(feats)


def fetch_csv(layer_url, dest, **kw):
    """Page a layer once and cache it as CSV. Returns dest."""
    dest = Path(dest)
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        df = pd.DataFrame(query_all(layer_url, **kw))
        df.drop(columns=[c for c in df.columns if c.startswith("Shape__")]).to_csv(dest, index=False)
    return dest
