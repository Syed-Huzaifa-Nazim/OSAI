"""Compare an account with accounts of a similar size (the 997 training accounts).

Nothing here is a typed-in cut-off. "Typical" is whatever the real accounts show:
the percentile of a value is the share of similar accounts at or below it, and the
typical range is the middle half of those accounts (25th to 75th percentile).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

PATH = Path(__file__).with_name("peer_benchmark.json")
_data: dict[str, Any] | None = None
_loaded = False


def _load() -> dict[str, Any] | None:
    global _data, _loaded
    if not _loaded:
        _data = json.loads(PATH.read_text()) if PATH.exists() else None
        _loaded = True
    return _data


def available() -> bool:
    return _load() is not None


def band_of(followers: float) -> str:
    """small / medium / large: the three equal-sized follower groups of the training accounts."""
    low, high = _load()["band_edges"]
    return "small" if followers <= low else "medium" if followers <= high else "large"


def reference_range() -> tuple[int, int]:
    """Smallest and largest follower count among the reference accounts."""
    bands = _load()["bands"]
    return int(bands["small"]["followers_min"]), int(bands["large"]["followers_max"])


def in_range(followers: float | None) -> bool:
    """Can this account fairly be compared with 'accounts of its size'? Only inside the reference range."""
    if not followers:
        return False
    lo, hi = reference_range()
    return lo <= followers <= hi


def band_info(band: str) -> dict[str, Any]:
    b = _load()["bands"][band]
    return {"followers_min": b["followers_min"], "followers_max": b["followers_max"], "n_accounts": b["n_accounts"]}


def _values(metric: str, band: str) -> np.ndarray:
    return np.asarray(_load()["bands"][band]["metrics"].get(metric, []), dtype=float)


def percentile(metric: str, band: str, value: float | None) -> float | None:
    """0-100: share of similar accounts at or below this value (ties count half)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    vals = _values(metric, band)
    if len(vals) == 0:
        return None
    below, equal = float((vals < value).sum()), float((vals == value).sum())
    return round(100.0 * (below + 0.5 * equal) / len(vals), 1)


def typical_range(metric: str, band: str) -> tuple[float, float] | None:
    """The middle half of similar accounts: (25th percentile value, 75th percentile value)."""
    vals = _values(metric, band)
    if len(vals) == 0:
        return None
    return float(np.percentile(vals, 25)), float(np.percentile(vals, 75))


def share_yes(metric: str, band: str) -> float | None:
    """For yes/no habits: the share of similar accounts that do it (0-1)."""
    vals = _values(metric, band)
    return None if len(vals) == 0 else float(vals.mean())


def association(metric: str) -> dict[str, Any] | None:
    """Does this habit go with engagement among similar-size accounts? {rho, p, n, significant} (see the builder)."""
    return _load().get("associations", {}).get(metric)


def quarter(percentile_value: float | None) -> int | None:
    """Which quarter of similar accounts: 0 = bottom quarter ... 3 = top quarter."""
    if percentile_value is None:
        return None
    return 0 if percentile_value < 25 else 1 if percentile_value < 50 else 2 if percentile_value < 75 else 3
