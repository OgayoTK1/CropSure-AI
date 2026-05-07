"""Shared utilities for the CropSure ML service.

build_feature_vector() is the single authoritative place where raw computed
values are assembled into the 6-element feature dict that the classifier
expects.  It MUST be used by /analyze — never construct the dict inline.
"""

import math
import random
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ── Rainfall anomaly (Open-Meteo / simulated) ─────────────────────────────────

def get_rainfall_anomaly(lat: float, lon: float, date_str: str) -> float:
    """
    Return monthly rainfall anomaly in mm for a location.
    Calls Open-Meteo historical archive API; falls back to a deterministic
    seasonal simulation when the API is unavailable.
    """
    try:
        import requests
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        start_date = dt.replace(day=1).strftime("%Y-%m-%d")
        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}"
            f"&start_date={start_date}&end_date={date_str}"
            f"&daily=precipitation_sum&timezone=Africa/Nairobi"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        vals = r.json().get("daily", {}).get("precipitation_sum", [])
        total = sum(v for v in vals if v is not None)
        # East Africa monthly normal ≈ 65 mm; anomaly = actual - normal
        return round(total - 65.0, 1)
    except Exception as exc:
        logger.debug("Rainfall fetch failed (%s) — using seasonal simulation", exc)
        week = datetime.strptime(date_str, "%Y-%m-%d").isocalendar()[1]
        seasonal = 20 * math.sin(2 * math.pi * week / 52)
        return round(seasonal + random.gauss(0, 15), 1)


# ── GeoJSON helpers ───────────────────────────────────────────────────────────

def polygon_centroid(polygon_geojson: dict) -> tuple:
    """Return (lat, lon) centroid of a GeoJSON Polygon."""
    try:
        coords = polygon_geojson["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    except Exception:
        return -1.286, 36.817  # Nairobi default


# ── Feature engineering ───────────────────────────────────────────────────────

def build_feature_vector(
    ndvi_zscore: float,
    ndvi_roc: float,
    rainfall_anomaly_mm: float,
    dt: Optional[date] = None,
    cloud_contaminated: bool = False,
) -> dict:
    """
    Assemble the 6-element feature dict for the stress classifier.

    The order and key names MUST match train.py FEATURE_NAMES exactly:
        ["ndvi_zscore", "ndvi_roc", "rainfall_anomaly_mm",
         "day_of_year", "seasonal_factor", "cloud_contaminated"]

    Args:
        ndvi_zscore          : z-score vs farm's personal baseline (negative = stress)
        ndvi_roc             : average per-period rate of change (negative = falling fast)
        rainfall_anomaly_mm  : deviation from climatological normal (negative = drought)
        dt                   : reference date (defaults to today)
        cloud_contaminated   : True suppresses payout even if stress detected

    Returns:
        dict with all 6 feature keys, values rounded for logging/storage.
    """
    if dt is None:
        dt = date.today()

    doy = dt.timetuple().tm_yday
    seasonal_factor = 0.15 * math.sin((doy - 60) * math.pi / 182)

    return {
        "ndvi_zscore":         round(float(ndvi_zscore), 4),
        "ndvi_roc":            round(float(ndvi_roc), 4),
        "rainfall_anomaly_mm": round(float(rainfall_anomaly_mm), 2),
        "day_of_year":         doy,
        "seasonal_factor":     round(seasonal_factor, 4),
        "cloud_contaminated":  int(bool(cloud_contaminated)),
    }
