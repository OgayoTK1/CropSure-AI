"""
baseline.py — Farm NDVI baseline builder for CropSure AI.

Builds each farm's personal NDVI "fingerprint" from 5 years of
satellite history and uses it to compute z-scores that drive the
stress classifier.  Per-farm baselines are the core differentiator
that eliminates the basis-risk problem plaguing ACRE Africa / Pula.

Author: CropSure ML Team (Member 1)
"""

import math
import logging
from collections import defaultdict
from sentinel import get_historical_ndvi

logger = logging.getLogger(__name__)

# Minimum observations per week to trust the baseline
MIN_SAMPLES = 2


def build_farm_baseline(polygon_geojson: dict, years: int = 5) -> dict:
    """
    Build a farm's personal NDVI baseline from satellite history.

    Pulls the last `years` years of weekly NDVI readings for the exact
    farm polygon and computes the mean and standard deviation for each
    ISO week number (1–52).  Missing weeks are filled by interpolation
    from neighbouring weeks so every week always has a value.

    Args:
        polygon_geojson : GeoJSON geometry of the farm polygon
        years           : Number of historical years to include (default 5)

    Returns:
        Baseline dict  { "1": {"mean":0.61, "std":0.04, "sample_count":4}, ... }
        Keys are string week numbers "1"–"52".
    """
    logger.info("Building farm baseline from %d years of satellite data...", years)

    historical = get_historical_ndvi(polygon_geojson, years=years)

    # Group NDVI values by ISO week number
    weekly_values: dict = defaultdict(list)
    for record in historical:
        week  = record["week_of_year"]
        ndvi  = record["mean_ndvi"]
        if 0.0 < ndvi < 1.0:
            weekly_values[week].append(ndvi)

    # Compute mean + std per week where we have enough samples
    baseline: dict = {}
    for week, values in weekly_values.items():
        mean = sum(values) / len(values)
        if len(values) >= MIN_SAMPLES:
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = math.sqrt(variance)
        else:
            std = 0.04  # conservative fallback std

        baseline[str(week)] = {
            "mean":         round(mean, 4),
            "std":          round(max(std, 0.025), 4),   # floor std to avoid division by near-zero
            "sample_count": len(values),
        }

    # Fill any missing weeks by linear interpolation from neighbours
    for week in range(1, 53):
        if str(week) not in baseline:
            baseline[str(week)] = _interpolate_week(week, baseline)

    logger.info("Baseline complete: %d weeks covered.", len(baseline))
    return baseline


def compute_ndvi_zscore(current_ndvi: float, week_of_year: int, baseline: dict) -> float:
    """
    Compute how many standard deviations the current NDVI is below
    the farm's historical mean for this week of the year.

    A negative z-score means the current reading is below average.
    Values below –1.5 are strong indicators of crop stress.

    Args:
        current_ndvi : NDVI value from the most recent satellite pass
        week_of_year : ISO week number (1–52)
        baseline     : dict returned by build_farm_baseline()

    Returns:
        z-score (float).  Negative = below baseline (potential stress).
    """
    week_key  = str(week_of_year)
    week_data = baseline.get(week_key)

    if week_data is None:
        logger.warning("No baseline entry for week %d — returning 0.", week_of_year)
        return 0.0

    mean = week_data["mean"]
    std  = max(week_data["std"], 0.025)  # guard against near-zero std

    zscore = (current_ndvi - mean) / std
    return round(zscore, 4)


def compute_ndvi_deviation_pct(current_ndvi: float, week_of_year: int, baseline: dict) -> float:
    """
    Compute the percentage change from the baseline mean.

    Example: current = 0.42, baseline mean = 0.61 → deviation = -31.1 %
    This is the human-readable number used in payout notifications.

    Returns:
        Deviation percentage (negative = below baseline).
    """
    week_key  = str(week_of_year)
    week_data = baseline.get(week_key)

    if week_data is None or week_data["mean"] == 0:
        return 0.0

    deviation = (current_ndvi - week_data["mean"]) / week_data["mean"] * 100
    return round(deviation, 2)


def compute_rate_of_change(ndvi_history: list) -> float:
    """
    Compute the mean NDVI change per period over the last 3 readings.

    A strongly negative rate-of-change, combined with a low z-score,
    indicates rapid onset stress (e.g. sudden drought or flash flooding)
    versus a slow, gradual decline.

    Args:
        ndvi_history : list of recent NDVI values, oldest first.

    Returns:
        Mean per-period change (float).  Negative = declining NDVI.
    """
    if len(ndvi_history) < 2:
        return 0.0

    recent  = ndvi_history[-min(3, len(ndvi_history)):]
    changes = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    return round(sum(changes) / len(changes), 4)


# ── Private helper ─────────────────────────────────────────────────────────────

def _interpolate_week(week: int, baseline: dict) -> dict:
    """
    Fill a missing week by averaging its two nearest populated neighbours.
    Wraps correctly at the year boundary (week 52 → week 1).
    """
    prev_key = str(week - 1 if week > 1  else 52)
    next_key = str(week + 1 if week < 52 else 1)

    prev_mean = baseline.get(prev_key, {}).get("mean", 0.55)
    next_mean = baseline.get(next_key, {}).get("mean", 0.55)

    return {
        "mean":         round((prev_mean + next_mean) / 2, 4),
        "std":          0.04,
        "sample_count": 0,   # marks as interpolated
    }
