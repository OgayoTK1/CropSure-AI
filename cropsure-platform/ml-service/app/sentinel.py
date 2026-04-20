"""
sentinel.py — Sentinel Hub satellite integration for CropSure AI.

Fetches Sentinel-2 NDVI data for individual farm polygons using the
Sentinel Hub Statistical API. Falls back to realistic mock data when
credentials are not configured (safe for local development and demo).

Author: CropSure ML Team (Member 1)
"""

import os
import logging
import math
import hashlib
from datetime import datetime
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Sentinel Hub endpoints ────────────────────────────────────────────────────
SH_TOKEN_URL = (
    "https://services.sentinel-hub.com/auth/realms/main"
    "/protocol/openid-connect/token"
)
SH_STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"

CLOUD_COVER_THRESHOLD = 60.0  # flag reading unreliable above this %

# ── Evalscript: NDVI + cloud mask ─────────────────────────────────────────────
NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04","B08","CLM"], units: "REFLECTANCE" }],
    output: [
      { id: "ndvi",       bands: 1, sampleType: "FLOAT32" },
      { id: "cloud_mask", bands: 1, sampleType: "UINT8"   }
    ]
  };
}
function evaluatePixel(sample) {
  let denom = sample.B08 + sample.B04;
  let ndvi  = denom > 0 ? (sample.B08 - sample.B04) / denom : 0;
  return { ndvi: [ndvi], cloud_mask: [sample.CLM] };
}
"""

# ── Simple in-process token cache ─────────────────────────────────────────────
_token_cache: dict = {"token": None, "expires_at": 0.0}


def _get_access_token() -> Optional[str]:
    """
    Obtain an OAuth2 bearer token from Sentinel Hub.
    Caches it until 60 s before expiry.
    Returns None when credentials are absent (triggers mock fallback).
    """
    client_id = os.getenv("SENTINEL_HUB_CLIENT_ID", "")
    client_secret = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        logger.debug("Sentinel Hub credentials not set — mock data will be used.")
        return None

    now = datetime.utcnow().timestamp()
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    try:
        resp = requests.post(
            SH_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        resp.raise_for_status()
        payload = resp.json()
        _token_cache["token"] = payload["access_token"]
        _token_cache["expires_at"] = now + payload.get("expires_in", 3600) - 60
        logger.info("Sentinel Hub token refreshed successfully.")
        return _token_cache["token"]

    except requests.RequestException as exc:
        logger.error("Failed to obtain Sentinel Hub token: %s", exc)
        return None


def get_ndvi(polygon_geojson: dict, date_from: str, date_to: str) -> dict:
    """
    Fetch mean NDVI statistics for a farm polygon over a date range.

    Uses the Sentinel Hub Statistical API which aggregates pixel-level values
    server-side — returning only scalar statistics to keep latency under 3 s
    for typical smallholder farm sizes (1–5 acres / 0.4–2 ha).

    Args:
        polygon_geojson: GeoJSON geometry dict  e.g. {"type":"Polygon","coordinates":[...]}
        date_from:       ISO date string "YYYY-MM-DD"
        date_to:         ISO date string "YYYY-MM-DD"

    Returns:
        dict with keys:
            ndvi_mean         float   mean NDVI of all valid pixels
            ndvi_std          float   standard deviation of NDVI
            cloud_cover_pct   float   percentage of cloudy pixels (0-100)
            valid_pixels_pct  float   percentage of non-nodata pixels (0-100)
            date              str     date_from echoed
            cloud_contaminated bool   True when cloud_cover_pct > 60
    """
    token = _get_access_token()
    if token is None:
        return _mock_ndvi(polygon_geojson, date_from)

    payload = {
        "input": {
            "bounds": {"geometry": polygon_geojson},
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {
                        "from": f"{date_from}T00:00:00Z",
                        "to":   f"{date_to}T23:59:59Z",
                    },
                    "maxCloudCoverage": 100,
                },
            }],
        },
        "aggregation": {
            "timeRange": {
                "from": f"{date_from}T00:00:00Z",
                "to":   f"{date_to}T23:59:59Z",
            },
            "aggregationInterval": {"of": "P5D"},
            "evalscript": NDVI_EVALSCRIPT,
            "resx": 10,
            "resy": 10,
        },
    }

    try:
        resp = requests.post(
            SH_STATS_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type":  "application/json",
            },
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()

        intervals = data.get("data", [])
        if not intervals:
            logger.warning("No satellite intervals returned for %s — using mock.", date_from)
            return _mock_ndvi(polygon_geojson, date_from)

        latest      = intervals[-1]
        outputs     = latest.get("outputs", {})
        ndvi_stats  = outputs.get("ndvi",       {}).get("bands", {}).get("B0", {}).get("stats", {})
        cloud_stats = outputs.get("cloud_mask", {}).get("bands", {}).get("B0", {}).get("stats", {})

        ndvi_mean    = float(ndvi_stats.get("mean",        0.5))
        ndvi_std     = float(ndvi_stats.get("stDev",       0.05))
        cloud_mean   = float(cloud_stats.get("mean",       0.0))
        sample_count = int(ndvi_stats.get("sampleCount",  1))
        no_data      = int(ndvi_stats.get("noDataCount",  0))

        cloud_cover_pct  = round(cloud_mean * 100, 2)
        valid_pixels_pct = round(
            max(0.0, (sample_count - no_data) / max(sample_count, 1) * 100), 2
        )

        return {
            "ndvi_mean":          round(ndvi_mean, 4),
            "ndvi_std":           round(ndvi_std, 4),
            "cloud_cover_pct":    cloud_cover_pct,
            "valid_pixels_pct":   valid_pixels_pct,
            "date":               date_from,
            "cloud_contaminated": cloud_cover_pct > CLOUD_COVER_THRESHOLD,
        }

    except requests.RequestException as exc:
        logger.error("Sentinel Hub NDVI request failed: %s — using mock.", exc)
        return _mock_ndvi(polygon_geojson, date_from)


def get_historical_ndvi(polygon_geojson: dict, years: int = 5) -> list:
    """
    Retrieve weekly mean NDVI for a polygon going back `years` calendar years.

    Makes one Statistical API call per year with a 7-day aggregation interval.
    Only includes readings with 0 < NDVI < 1 and cloud cover < 60 %.

    Returns:
        List of dicts: [{week_of_year, mean_ndvi, year, date}, ...]
    """
    token = _get_access_token()
    if token is None:
        logger.warning("No Sentinel Hub token — returning mock historical NDVI.")
        return _mock_historical_ndvi(years)

    results = []
    today   = datetime.utcnow()

    for offset in range(years):
        year  = today.year - offset
        start = f"{year}-01-01"
        end   = f"{year}-12-31"

        payload = {
            "input": {
                "bounds": {"geometry": polygon_geojson},
                "data": [{
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": f"{start}T00:00:00Z",
                            "to":   f"{end}T23:59:59Z",
                        },
                        "maxCloudCoverage": 60,
                    },
                }],
            },
            "aggregation": {
                "timeRange": {
                    "from": f"{start}T00:00:00Z",
                    "to":   f"{end}T23:59:59Z",
                },
                "aggregationInterval": {"of": "P7D"},
                "evalscript": NDVI_EVALSCRIPT,
                "resx": 10,
                "resy": 10,
            },
        }

        try:
            resp = requests.post(
                SH_STATS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type":  "application/json",
                },
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()

            for interval in data.get("data", []):
                date_str   = interval["interval"]["from"][:10]
                date_obj   = datetime.strptime(date_str, "%Y-%m-%d")
                week       = date_obj.isocalendar()[1]
                ndvi_stats = (
                    interval.get("outputs", {})
                    .get("ndvi", {})
                    .get("bands", {})
                    .get("B0", {})
                    .get("stats", {})
                )
                mean_ndvi = ndvi_stats.get("mean")
                if mean_ndvi is not None and 0.0 < float(mean_ndvi) < 1.0:
                    results.append({
                        "week_of_year": week,
                        "mean_ndvi":    round(float(mean_ndvi), 4),
                        "year":         year,
                        "date":         date_str,
                    })

        except requests.RequestException as exc:
            logger.error("Historical NDVI fetch failed for year %d: %s — using mock.", year, exc)
            results.extend(_mock_historical_ndvi(1, base_year=year))

    logger.info("Historical NDVI: %d weekly records fetched across %d years.", len(results), years)
    return results


# ── Mock helpers ───────────────────────────────────────────────────────────────

def _mock_ndvi(polygon_geojson: dict, date_str: str) -> dict:
    """
    Deterministic, realistic mock NDVI for development / demo.
    Simulates East Africa's bimodal rainfall pattern.
    """
    coords     = polygon_geojson.get("coordinates", [[]])[0]
    coord_key  = str(coords[:2]) if coords else "nairobi"
    seed       = int(hashlib.md5(f"{coord_key}{date_str}".encode()).hexdigest()[:8], 16)

    try:
        month = int(date_str[5:7])
    except (IndexError, ValueError):
        month = 6

    # East Africa bimodal rainfall: long rains Mar-May, short rains Oct-Dec
    seasonal = (
        0.12 * math.sin((month - 3) * math.pi / 6) +
        0.07 * math.sin((month - 9) * math.pi / 3)
    )
    base = 0.52 + (seed % 100) / 500.0
    ndvi = max(0.2, min(0.85, base + seasonal))

    return {
        "ndvi_mean":          round(ndvi, 4),
        "ndvi_std":           0.04,
        "cloud_cover_pct":    12.0,
        "valid_pixels_pct":   94.0,
        "date":               date_str,
        "cloud_contaminated": False,
    }


def _mock_historical_ndvi(years: int, base_year: int = None) -> list:
    """Generate mock weekly NDVI for `years` years."""
    results  = []
    ref_year = base_year or (datetime.utcnow().year - 1)

    for offset in range(years):
        year = ref_year - offset
        for week in range(1, 53):
            seasonal = (
                0.12 * math.sin((week - 10) * math.pi / 26) +
                0.07 * math.sin((week - 40) * math.pi / 13)
            )
            noise = (hash(f"{year}{week}") % 200 - 100) / 5000.0
            ndvi  = max(0.2, min(0.85, 0.57 + seasonal + noise))
            results.append({
                "week_of_year": week,
                "mean_ndvi":    round(ndvi, 4),
                "year":         year,
                "date":         f"{year}-W{week:02d}",
            })

    return results
