"""
utils.py — Shared utilities for CropSure AI ML Service.

Covers:
    - GeoJSON polygon validation and area calculation
    - Date range helpers
    - NDVI value validation
    - Response formatting
    - Logging setup

Author: CropSure ML Team (Member 1)
"""

import math
import logging
import os
from datetime import date, datetime, timedelta
from typing import Optional

# ── Logging ───────────────────────────────────────────────────────────────────

def get_logger(name: str) -> logging.Logger:
    """
    Return a configured logger for a given module name.
    Uses LOG_LEVEL env var (default INFO).
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s  %(name)-25s %(levelname)-8s %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level, logging.INFO))
    return logger


logger = get_logger(__name__)


# ── GeoJSON helpers ───────────────────────────────────────────────────────────

def validate_polygon(polygon_geojson: dict) -> tuple[bool, str]:
    """
    Validate that a GeoJSON object is a well-formed Polygon.

    Returns:
        (is_valid: bool, error_message: str)
        error_message is empty string when valid.

    Rules:
        - Must have "type" == "Polygon"
        - Must have "coordinates" as a list with at least one ring
        - Outer ring must have at least 4 points (3 unique + closing point)
        - Closing point must equal first point
        - All coordinates must be valid longitude/latitude values
    """
    if not isinstance(polygon_geojson, dict):
        return False, "polygon_geojson must be a dict"

    geom_type = polygon_geojson.get("type")
    if geom_type != "Polygon":
        return False, f"Expected type 'Polygon', got '{geom_type}'"

    coords = polygon_geojson.get("coordinates")
    if not coords or not isinstance(coords, list) or len(coords) == 0:
        return False, "coordinates must be a non-empty list"

    outer_ring = coords[0]
    if not isinstance(outer_ring, list) or len(outer_ring) < 4:
        return False, "Outer ring must have at least 4 coordinate pairs"

    for i, point in enumerate(outer_ring):
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            return False, f"Point {i} is malformed: {point}"
        lng, lat = point[0], point[1]
        if not (-180 <= lng <= 180):
            return False, f"Point {i} longitude {lng} is out of range (-180 to 180)"
        if not (-90 <= lat <= 90):
            return False, f"Point {i} latitude {lat} is out of range (-90 to 90)"

    # Check ring is closed (last point == first point)
    first = outer_ring[0]
    last  = outer_ring[-1]
    if first[0] != last[0] or first[1] != last[1]:
        return False, "Outer ring is not closed (last point must equal first point)"

    return True, ""


def polygon_area_acres(polygon_geojson: dict) -> float:
    """
    Compute the approximate area of a GeoJSON Polygon in acres.

    Uses the Shoelace formula on coordinates converted to metres via
    an equirectangular projection centred on the polygon centroid.
    Accurate to within ~2% for typical smallholder farm sizes (< 10 ha).

    Args:
        polygon_geojson: valid GeoJSON Polygon geometry

    Returns:
        Area in acres (float). Returns 0.0 if polygon is invalid.
    """
    try:
        coords = polygon_geojson["coordinates"][0]
        if len(coords) < 3:
            return 0.0

        # Compute centroid latitude for projection scaling
        lats = [p[1] for p in coords]
        lngs = [p[0] for p in coords]
        lat_c = sum(lats) / len(lats)

        # Degrees → metres conversion factors at centroid latitude
        M_PER_DEG_LAT = 111_320.0
        M_PER_DEG_LNG = 111_320.0 * math.cos(math.radians(lat_c))

        # Shoelace formula
        area_sq_m = 0.0
        n = len(coords)
        for i in range(n):
            j = (i + 1) % n
            x_i = coords[i][0] * M_PER_DEG_LNG
            y_i = coords[i][1] * M_PER_DEG_LAT
            x_j = coords[j][0] * M_PER_DEG_LNG
            y_j = coords[j][1] * M_PER_DEG_LAT
            area_sq_m += x_i * y_j
            area_sq_m -= x_j * y_i

        area_sq_m = abs(area_sq_m) / 2.0
        area_acres = area_sq_m / 4_046.856   # 1 acre = 4046.856 m²
        return round(area_acres, 3)

    except Exception as exc:
        logger.error("Area calculation failed: %s", exc)
        return 0.0


def polygon_centroid(polygon_geojson: dict) -> tuple[float, float]:
    """
    Compute the centroid (longitude, latitude) of a GeoJSON Polygon.

    Returns:
        (longitude, latitude) tuple.
    """
    try:
        coords = polygon_geojson["coordinates"][0]
        lng = sum(p[0] for p in coords) / len(coords)
        lat = sum(p[1] for p in coords) / len(coords)
        return round(lng, 6), round(lat, 6)
    except Exception:
        return 36.8219, -1.2921   # Nairobi default


# ── Date helpers ──────────────────────────────────────────────────────────────

def current_date_window(lookback_days: int = 5) -> tuple[str, str]:
    """
    Return (date_from, date_to) strings for a recent satellite fetch window.

    Args:
        lookback_days: how many days back to start the window (default 5)

    Returns:
        ("YYYY-MM-DD", "YYYY-MM-DD")
    """
    today     = date.today()
    date_to   = today.isoformat()
    date_from = (today - timedelta(days=lookback_days)).isoformat()
    return date_from, date_to


def week_of_year(dt: Optional[date] = None) -> int:
    """Return ISO week number (1–52) for a given date (default: today)."""
    if dt is None:
        dt = date.today()
    return dt.isocalendar()[1]


def day_of_year(dt: Optional[date] = None) -> int:
    """Return day of year (1–365) for a given date (default: today)."""
    if dt is None:
        dt = date.today()
    return dt.timetuple().tm_yday


def month_name_en(month: int) -> str:
    """Return English month name for a given month number (1–12)."""
    months = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December",
    ]
    return months[max(0, min(11, month - 1))]


def month_name_sw(month: int) -> str:
    """Return Swahili month name for a given month number (1–12)."""
    months = [
        "Januari","Februari","Machi","Aprili","Mei","Juni",
        "Julai","Agosti","Septemba","Oktoba","Novemba","Desemba",
    ]
    return months[max(0, min(11, month - 1))]


# ── NDVI validation ───────────────────────────────────────────────────────────

def is_valid_ndvi(value: float) -> bool:
    """
    Check whether an NDVI value is physically plausible.

    NDVI ranges from -1 to +1 theoretically.
    For vegetated land we expect 0.05 to 0.95.
    Values outside 0.0–1.0 indicate sensor error or non-vegetated surface.
    """
    return isinstance(value, (int, float)) and 0.0 <= float(value) <= 1.0


def clamp_ndvi(value: float) -> float:
    """Clamp an NDVI value to the valid range [0.0, 1.0]."""
    return round(max(0.0, min(1.0, float(value))), 4)


def ndvi_health_label(ndvi: float) -> str:
    """
    Convert an NDVI value to a human-readable health label.
    Used in dashboard display and notifications.
    """
    if ndvi >= 0.70:
        return "excellent"
    if ndvi >= 0.55:
        return "good"
    if ndvi >= 0.40:
        return "moderate"
    if ndvi >= 0.25:
        return "poor"
    return "critical"


def ndvi_health_color(ndvi: float) -> str:
    """Return a hex colour for the dashboard farm marker based on NDVI."""
    if ndvi >= 0.60:
        return "#1D9E75"   # green — healthy
    if ndvi >= 0.45:
        return "#F39C12"   # amber — watch
    return "#E74C3C"       # red   — stressed / payout triggered


# ── Payout calculation ────────────────────────────────────────────────────────

def compute_payout_amount(
    coverage_amount_kes: float,
    stress_type: str,
    confidence: float,
    ndvi_deviation_pct: float,
) -> float:
    """
    Compute the payout amount as a fraction of the total coverage.

    Payout tiers based on stress severity:
        Mild   (deviation 15–25%): 30% of coverage
        Moderate (25–40%):         50% of coverage
        Severe   (> 40%):          80% of coverage

    Confidence acts as a scaling factor above the 0.72 trigger threshold.

    Args:
        coverage_amount_kes: total policy coverage in KES
        stress_type:         "drought" | "flood" | "pest_disease"
        confidence:          model confidence score (0–1)
        ndvi_deviation_pct:  negative percentage deviation from baseline

    Returns:
        Payout amount in KES, rounded to nearest 50.
    """
    deviation_abs = abs(ndvi_deviation_pct)

    if deviation_abs >= 40:
        base_fraction = 0.80
    elif deviation_abs >= 25:
        base_fraction = 0.50
    else:
        base_fraction = 0.30

    # Scale by confidence above the 0.72 threshold
    # confidence=0.72 → scale=1.0, confidence=1.0 → scale=1.15
    confidence_scale = 1.0 + max(0.0, (confidence - 0.72) / 0.28 * 0.15)

    raw_amount = coverage_amount_kes * base_fraction * confidence_scale
    # Round to nearest 50 KES
    rounded = round(raw_amount / 50) * 50
    return float(max(50.0, rounded))


# ── Response helpers ──────────────────────────────────────────────────────────

def error_response(message: str, code: int = 400) -> dict:
    """Standard error response format."""
    return {
        "error":   True,
        "message": message,
        "code":    code,
    }


def success_response(data: dict, message: str = "ok") -> dict:
    """Standard success response wrapper."""
    return {
        "success": True,
        "message": message,
        "data":    data,
    }


# ── Feature vector builder ────────────────────────────────────────────────────

def build_feature_vector(
    ndvi_zscore:         float,
    ndvi_roc:            float,
    rainfall_anomaly_mm: float,
    dt:                  Optional[date] = None,
    cloud_contaminated:  bool = False,
) -> dict:
    """
    Build the feature dict expected by model.predict_stress().

    This is the single source of truth for feature construction — both
    the main /analyze endpoint and the monitoring cron job should call
    this function to ensure consistency with the training pipeline.

    Args:
        ndvi_zscore:          z-score vs farm personal baseline
        ndvi_roc:             3-period mean rate of change
        rainfall_anomaly_mm:  deviation from climatological normal
        dt:                   date for seasonal features (default: today)
        cloud_contaminated:   True when cloud cover > 60%

    Returns:
        Dict with keys: ndvi_zscore, ndvi_roc, rainfall_anomaly_mm,
        day_of_year, seasonal_factor, cloud_contaminated
    """
    if dt is None:
        dt = date.today()

    doy = dt.timetuple().tm_yday
    seasonal = 0.15 * math.sin((doy - 60) * math.pi / 182)

    return {
        "ndvi_zscore":         round(float(ndvi_zscore), 4),
        "ndvi_roc":            round(float(ndvi_roc), 4),
        "rainfall_anomaly_mm": round(float(rainfall_anomaly_mm), 2),
        "day_of_year":         doy,
        "seasonal_factor":     round(seasonal, 4),
        "cloud_contaminated":  int(cloud_contaminated),
    }
