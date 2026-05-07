"""Per-farm NDVI baseline builder and z-score / deviation calculators.

All functions in this module operate on the farm's *personal* historical
baseline — never a regional average. This is the core concept that
separates CropSure from every existing solution.

Baseline dict shape:
    {
        "1":  {"mean": 0.52, "std": 0.04, "sample_count": 4},
        "2":  {"mean": 0.54, "std": 0.03, "sample_count": 5},
        ...
        "52": {"mean": 0.58, "std": 0.05, "sample_count": 4},
    }
Week keys are strings so they serialise cleanly to/from JSON / PostgreSQL.
"""

import logging
import math
from collections import defaultdict
from typing import Optional

from .sentinel import get_historical_ndvi

logger = logging.getLogger(__name__)

# Minimum std — prevents divide-by-zero and unrealistically tight z-scores
# on farms with very stable NDVI histories.
STD_FLOOR = 0.025


# ── Baseline builder ──────────────────────────────────────────────────────────

def build_farm_baseline(polygon_geojson: dict, years: int = 5) -> dict:
    """
    Fetch N years of weekly NDVI history for a polygon and compute per-week
    mean and standard deviation.

    Returns: {week_number_str: {"mean": float, "std": float, "sample_count": int}}
    """
    logger.info("Building baseline — fetching %d years of NDVI history", years)
    readings = get_historical_ndvi(polygon_geojson, years=years)

    weekly: dict = defaultdict(list)
    for r in readings:
        if not r.get("cloud_contaminated") and r.get("mean_ndvi") is not None:
            ndvi = float(r["mean_ndvi"])
            if 0.0 < ndvi < 1.0:   # discard obviously bad readings
                weekly[r["week_of_year"]].append(ndvi)

    baseline = {}
    for week, values in weekly.items():
        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
        std = math.sqrt(variance)
        baseline[str(week)] = {
            "mean": round(mean, 4),
            "std": round(max(std, STD_FLOOR), 4),  # floor prevents div-by-zero
            "sample_count": n,
        }

    logger.info("Baseline built — %d weeks covered from %d readings", len(baseline), len(readings))
    return baseline


# ── Z-score and deviation ─────────────────────────────────────────────────────

def compute_ndvi_zscore(
    current_ndvi: float,
    week_of_year: int,
    baseline: dict,
) -> Optional[float]:
    """
    How many standard deviations is current_ndvi below this farm's normal?

    z = (current - historical_mean) / historical_std

    Negative z-score = stress.  z < -2 = severe stress.
    Returns None when the week is absent from the baseline (handled by caller).
    """
    key = str(week_of_year)

    # Try ±2 week window when exact week is missing (sparse baseline gaps)
    if key not in baseline:
        for offset in [1, -1, 2, -2]:
            alt = str(week_of_year + offset)
            if alt in baseline:
                key = alt
                break
        else:
            logger.debug("No baseline data near week %d", week_of_year)
            return None

    mean = baseline[key]["mean"]
    std = max(float(baseline[key]["std"]), STD_FLOOR)  # safety floor at read time too
    return round((current_ndvi - mean) / std, 3)


def ndvi_deviation_pct(
    current_ndvi: float,
    week_of_year: int,
    baseline: dict,
) -> Optional[float]:
    """
    Percentage deviation from the farm's historical mean for this week.
    Negative = below baseline.  e.g. -38 means 38% below normal.
    """
    key = str(week_of_year)
    if key not in baseline:
        return None
    mean = baseline[key]["mean"]
    if mean == 0:
        return None
    return round((current_ndvi - mean) / mean * 100, 1)


# ── Rate of change ────────────────────────────────────────────────────────────

def compute_rate_of_change(ndvi_series: list) -> float:
    """
    Average per-period NDVI change across the last 3 readings.

    Positive  = crops are getting greener (recovering / growing).
    Negative  = crops are declining (stress developing).
    Near zero = stable.

    Examples:
        [0.68, 0.61, 0.54]  →  -0.07  (rapid decline — drought signal)
        [0.52, 0.55, 0.59]  →  +0.035 (recovery)
    """
    if len(ndvi_series) < 2:
        return 0.0
    recent = ndvi_series[-3:]
    diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    return round(sum(diffs) / len(diffs), 4)
