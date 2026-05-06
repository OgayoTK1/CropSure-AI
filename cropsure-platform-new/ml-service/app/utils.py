"""Shared utilities for the ML service."""

import math
import random
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def get_rainfall_anomaly(lat: float, lon: float, date_str: str) -> float:
    """
    Return rainfall anomaly in mm for a location.
    Uses Open-Meteo API if available, otherwise simulates based on East Africa seasonality.
    """
    try:
        import requests
        date = datetime.strptime(date_str, "%Y-%m-%d")
        end_date = date_str
        start_date = date.replace(day=1).strftime("%Y-%m-%d")
        url = (
            f"https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}"
            f"&daily=precipitation_sum&timezone=Africa/Nairobi"
        )
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        vals = r.json().get("daily", {}).get("precipitation_sum", [])
        total = sum(v for v in vals if v is not None)
        # East Africa monthly normal ~65mm; anomaly = actual - normal
        return round(total - 65.0, 1)
    except Exception as e:
        logger.debug("Rainfall fetch failed (%s) — simulating", e)
        week = datetime.strptime(date_str, "%Y-%m-%d").isocalendar()[1]
        seasonal = 20 * math.sin(2 * math.pi * week / 52)
        return round(seasonal + random.gauss(0, 15), 1)


def compute_rate_of_change(ndvi_series: list) -> float:
    """Return average per-period NDVI change over last 3 readings."""
    if len(ndvi_series) < 2:
        return 0.0
    recent = ndvi_series[-3:]
    diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    return round(sum(diffs) / len(diffs), 4)


def polygon_centroid(polygon_geojson: dict) -> tuple:
    """Return (lat, lon) centroid of a GeoJSON Polygon."""
    try:
        coords = polygon_geojson["coordinates"][0]
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    except Exception:
        return -1.286, 36.817  # Nairobi default
