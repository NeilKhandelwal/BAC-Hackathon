"""Shared test helpers."""
from pathlib import Path

import pytest

RAW = "data/raw"


def require_raw(*files):
    """Skip, with the reason in the report, when raw downloads are absent. Never download.

    The demo machine may be offline. Run `python -m etl.build_features` once to fetch them.
    """
    missing = [f for f in files if not (Path(RAW) / f).exists()]
    if missing:
        pytest.skip(f"raw files absent, run python -m etl.build_features to fetch: {missing}")
