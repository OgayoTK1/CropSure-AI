"""Per-farm NDVI baseline builder and z-score calculator."""

import logging
from collections import defaultdict
from typing import Optional

from .sentinel import get_historical_ndvi

logger = logging.getLogger(__name__)


def build_farm_baseline(polygon_geojson: dict, years: int = 5) -> dict:
    """
    Fetch 5-year weekly NDVI history and compute per-week mean/std.
    Returns: {week_number: {"mean": float, "std": float, "sample_count": int}}
    """
    logger.info("Building baseline — fetching %d years of NDVI history", years)
    readings = get_historical_ndvi(polygon_geojson, years=years)

    weekly: dict = defaultdict(list)
    for r in readings:
        if not r.get("cloud_contaminated") and r.get("mean_ndvi") is not None:
            weekly[r["week_of_year"]].append(r["mean_ndvi"])

    baseline = {}
    for week, values in weekly.items():
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
        std = variance ** 0.5
        baseline[str(week)] = {
            "mean": round(mean, 4),
            "std": round(max(std, 0.01), 4),  # floor std to avoid divide-by-zero
            "sample_count": n,
        }
    logger.info("Baseline built with %d weeks of data", len(baseline))
    return baseline


def compute_ndvi_zscore(current_ndvi: float, week_of_year: int, baseline: dict) -> Optional[float]:
    """
    Return how many std deviations current_ndvi is below the historical mean.
    Negative z-score = stress. Returns None if week not in baseline.
    """
    key = str(week_of_year)
    if key not in baseline:
        # Try ±2 week window if exact week missing (early season gap)
        for offset in [1, -1, 2, -2]:
            alt_key = str(week_of_year + offset)
            if alt_key in baseline:
                key = alt_key
                break
        else:
            return None

    week_data = baseline[key]
    mean = week_data["mean"]
    std = week_data["std"]
    return round((current_ndvi - mean) / std, 3)


def ndvi_deviation_pct(current_ndvi: float, week_of_year: int, baseline: dict) -> Optional[float]:
    """Return percentage deviation from historical mean (negative = below baseline)."""
    key = str(week_of_year)
    if key not in baseline:
        return None
    mean = baseline[key]["mean"]
    if mean == 0:
        return None
    return round((current_ndvi - mean) / mean * 100, 1)
