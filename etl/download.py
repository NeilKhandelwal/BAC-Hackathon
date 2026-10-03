"""Cached downloads into data/raw/. Fails loud on bot-challenge pages and truncated files."""
from pathlib import Path

import requests

# eta-publications.lbl.gov serves a Cloudflare challenge page to non-browser agents.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
ZIP_MAGIC = b"PK\x03\x04"  # zip, xlsx


def download(url, dest, min_bytes=1, magic=None, headers=None, timeout=300):
    """Download url to dest unless dest already exists. Returns dest."""
    dest = Path(dest)
    if dest.exists():
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, headers={"User-Agent": UA, **(headers or {})}, timeout=timeout)
    r.raise_for_status()
    body = r.content
    if len(body) < min_bytes or (magic and not body.startswith(magic)):
        raise RuntimeError(
            f"{url}: got {len(body)} bytes, content-type {r.headers.get('content-type')}. "
            "Expected a data file, not an error or challenge page.")
    dest.write_bytes(body)
    return dest
