"""Collect data center news URLs from the GDELT DOC 2.0 API.

Run this on a machine with open internet access. The cloud sandbox used for
research blocks gdeltproject.org.

Usage:
    python etl/gdelt_probe.py --start 2025-01-01 --end 2025-12-31 \
        --out data/raw/gdelt_urls.csv

What it does:
    1. Slices the date range into 7-day windows.
    2. For each window and each query, calls the artlist endpoint
       (max 250 records per call).
    3. Writes a deduplicated CSV of url, title, domain, seendate, query.

Then upload the CSV to BigQuery as table `urls` and run
etl/gdelt_gkg_county.sql with Filter 1 enabled to get county codes and tone.

Notes:
    - The API officially covers the last 3 months. Older windows usually still
      return results but are not guaranteed. Check the hit counts per window.
    - No API key. Be polite: one request every few seconds. The script sleeps
      between calls and backs off on HTTP 429.
    - 250 records per call is the ceiling. If a window hits 250, shrink the
      window (--days 3) and rerun.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import sys
import time
from pathlib import Path

import requests

API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Each query is run separately so the 250-record cap applies per query.
QUERIES = [
    '"data center" (rezoning OR rezone OR "zoning board" OR "planning commission") sourcecountry:US',
    '"data center" (moratorium OR "opposition" OR residents OR "town hall" OR petition) sourcecountry:US',
    '"data center" (water OR noise OR "electric bills" OR farmland) (residents OR county) sourcecountry:US',
    '"data center" (approved OR "tax abatement" OR incentives) (county OR "city council") sourcecountry:US',
]


def fmt(d: dt.date, end: bool = False) -> str:
    return d.strftime("%Y%m%d") + ("235959" if end else "000000")


def fetch(query: str, start: dt.date, end: dt.date, pause: float) -> list[dict]:
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": 250,
        "sort": "datedesc",
        "startdatetime": fmt(start),
        "enddatetime": fmt(end, end=True),
    }
    for attempt in range(5):
        r = requests.get(API, params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(pause * (2 ** attempt))
            continue
        r.raise_for_status()
        try:
            return r.json().get("articles", [])
        except ValueError:
            # GDELT returns plain text on query errors.
            print(f"non-JSON response for window {start}..{end}: {r.text[:200]}", file=sys.stderr)
            return []
    print(f"gave up on window {start}..{end} after 5 attempts", file=sys.stderr)
    return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--end", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--days", type=int, default=7, help="window length in days")
    ap.add_argument("--pause", type=float, default=5.0, help="seconds between calls")
    ap.add_argument("--out", type=Path, default=Path("data/raw/gdelt_urls.csv"))
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    rows: list[dict] = []

    cur = args.start
    while cur <= args.end:
        win_end = min(cur + dt.timedelta(days=args.days - 1), args.end)
        for q in QUERIES:
            arts = fetch(q, cur, win_end, args.pause)
            if len(arts) >= 250:
                print(f"window {cur}..{win_end} hit the 250 cap for a query; use --days smaller",
                      file=sys.stderr)
            for a in arts:
                u = a.get("url")
                if not u or u in seen:
                    continue
                seen.add(u)
                rows.append({
                    "url": u,
                    "title": a.get("title", ""),
                    "domain": a.get("domain", ""),
                    "seendate": a.get("seendate", ""),
                    "query": q,
                })
            time.sleep(args.pause)
        print(f"{cur}..{win_end}: {len(rows)} urls so far", file=sys.stderr)
        cur = win_end + dt.timedelta(days=1)

    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["url", "title", "domain", "seendate", "query"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} urls to {args.out}")


if __name__ == "__main__":
    main()
