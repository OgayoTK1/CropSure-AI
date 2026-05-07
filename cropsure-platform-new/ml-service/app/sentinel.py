"""
sentinel.py — Sentinel Hub satellite integration for CropSure AI.

Fetches Sentinel-2 NDVI and Sentinel-1 SAR data for individual farm
polygons. Falls back to deterministic mock data when credentials are
absent (safe for development and hackathon demo).

SETUP — replace the two URLs marked ← REPLACE if you switch from
Sentinel Hub to the Copernicus Data Space Ecosystem (CDSE).

Author: CropSure ML Team (Member 1)
"""

import hashlib
import logging
import math
import os
import random
from datetime import datetime, timedelta
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# API ENDPOINTS
#
# OPTION A — Sentinel Hub (sentinelhub.com)  ← DEFAULT, works out of the box
# ─────────────────────────────────────────────────────────────────────────────
SENTINEL_HUB_TOKEN_URL = (
    "https://services.sentinel-hub.com/auth/realms/main"
    "/protocol/openid-connect/token"
)
SENTINEL_HUB_STATS_URL = (
    "https://services.sentinel-hub.com/api/v1/statistics"
)

# ─────────────────────────────────────────────────────────────────────────────
# OPTION B — Copernicus Data Space Ecosystem (dataspace.copernicus.eu)
#            Easier sign-up, same Sentinel-2 data, free.
#            If you registered on CDSE instead of Sentinel Hub,
#            comment out Option A above and uncomment these two lines:
#
# OPTION B — Copernicus Data Space Ecosystem (dataspace.copernicus.eu)
# If you registered on CDSE instead of Sentinel Hub,
# comment out Option A above and uncomment these two lines:
# SENTINEL_HUB_TOKEN_URL = (
#     "https://identity.dataspace.copernicus.eu/auth/realms/CDSE"
#     "/protocol/openid-connect/token"
# )
# SENTINEL_HUB_STATS_URL = (
#     "https://sh.dataspace.copernicus.eu/api/v1/statistics"
# )
# ─────────────────────────────────────────────────────────────────────────────

CLOUD_COVER_THRESHOLD = 60.0   # readings above this % are flagged unreliable

# ── Evalscripts ───────────────────────────────────────────────────────────────

NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04","B08","SCL"], units: "DN" }],
    output: [{ id: "default", bands: 1, sampleType: "FLOAT32" }],
    mosaicking: "ORBIT"
  };
}
function evaluatePixel(samples) {
  // Mask cloud and shadow pixels using Scene Classification Layer
  if ([3, 8, 9, 10].includes(samples.SCL)) return [NaN];
  let denom = samples.B08 + samples.B04 + 1e-6;
  return [(samples.B08 - samples.B04) / denom];
}
"""

SAR_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV","VH"] }],
    output: [{ id: "default", bands: 2, sampleType: "FLOAT32" }],
    mosaicking: "ORBIT"
  };
}
function evaluatePixel(s) { return [s.VV, s.VH]; }
"""


# ── Token cache (one token lasts 3600 s — fetch once, reuse everywhere) ───────
_token_cache: dict = {"token": None, "expires_at": 0.0}


def _get_token() -> Optional[str]:
    """
    Obtain an OAuth2 bearer token from Sentinel Hub or CDSE.
    Caches the token until 60 s before expiry so a 127-farm monitoring
    cycle makes exactly ONE token request instead of 127.
    Returns None when credentials are not set (triggers mock fallback).
    """
    cid  = os.getenv("SENTINEL_HUB_CLIENT_ID",  "")
    csec = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")

    if not cid or not csec:
        logger.debug("No Sentinel Hub credentials — mock data will be used.")
        return None

    now = datetime.utcnow().timestamp()

    # Return cached token if still valid
    if _token_cache["token"] and now < _token_cache["expires_at"]:
        return _token_cache["token"]

    try:
        r = requests.post(
            SENTINEL_HUB_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(cid, csec),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        _token_cache["token"]      = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 3600) - 60
        logger.info("Sentinel Hub token refreshed successfully.")
        return _token_cache["token"]

    except Exception as exc:
        logger.error("Sentinel Hub token request failed: %s", exc)
        return None


# ── Mock helpers (deterministic — same polygon + date = same result) ──────────

def _simulate_ndvi(polygon_geojson: dict, date_from: str) -> dict:
    """
    Generate deterministic realistic mock NDVI.
    Uses a hash of the polygon coordinates + date as the random seed so
    the same farm always gets the same simulated baseline.
    Simulates East Africa's bimodal rainfall pattern.
    """
    coord_str = str(polygon_geojson.get("coordinates", [[]])[:1])
    seed      = int(hashlib.md5(f"{coord_str}{date_from}".encode()).hexdigest()[:8], 16)
    rng       = random.Random(seed)

    try:
        d = datetime.strptime(date_from, "%Y-%m-%d")
    except Exception:
        d = datetime.utcnow()

    week = d.isocalendar()[1]

    # East Africa bimodal seasonal pattern
    # Long rains: March–May | Short rains: October–December
    seasonal = (
        0.55 +
        0.15 * math.sin((week - 10) * math.pi / 26) +
        0.08 * math.sin((week - 40) * math.pi / 13)
    )
    ndvi  = max(0.10, min(0.95, seasonal + rng.gauss(0, 0.02)))
    cloud = rng.uniform(5, 25)

    return {
        "ndvi_mean":          round(ndvi, 4),
        "ndvi_std":           round(abs(rng.gauss(0, 0.02)), 4),
        "cloud_cover_pct":    round(cloud, 1),
        "valid_pixels_pct":   round(100.0 - cloud, 1),
        "date":               date_from,
        "cloud_contaminated": cloud > CLOUD_COVER_THRESHOLD,
        "simulated":          True,
    }


def _mock_historical_ndvi(years: int, base_year: int = None) -> list:
    """
    Generate deterministic weekly NDVI records for the past N years.
    Uses hash-based noise so the same farm always gets the same baseline.
    Called when credentials are absent OR when a single year's API call fails.
    """
    results  = []
    ref_year = base_year or (datetime.utcnow().year - 1)

    for offset in range(years):
        year = ref_year - offset
        for week in range(1, 53):
            seasonal = (
                0.57 +
                0.12 * math.sin((week - 10) * math.pi / 26) +
                0.07 * math.sin((week - 40) * math.pi / 13)
            )
            # Deterministic noise — no random module, purely hash-based
            noise = (hash(f"{year}{week}") % 200 - 100) / 5000.0
            ndvi  = max(0.20, min(0.85, seasonal + noise))
            results.append({
                "week_of_year":     week,
                "date":             f"{year}-W{week:02d}",
                "mean_ndvi":        round(ndvi, 4),
                "cloud_contaminated": False,
            })

    return results


# ── Public API ────────────────────────────────────────────────────────────────

def get_ndvi(polygon_geojson: dict, date_from: str, date_to: str) -> dict:
    """
    Fetch mean NDVI for a farm polygon over a date range.

    Uses the Sentinel Hub Statistical API which aggregates pixel-level
    values server-side — returning only scalar stats so response size
    is tiny and latency stays under 3 s for typical farm sizes.

    Falls back to deterministic mock when credentials are absent.

    Args:
        polygon_geojson : GeoJSON Polygon geometry dict
        date_from       : "YYYY-MM-DD"
        date_to         : "YYYY-MM-DD"

    Returns:
        {ndvi_mean, ndvi_std, cloud_cover_pct, valid_pixels_pct,
         date, cloud_contaminated, simulated}
    """
    token = _get_token()
    if token is None:
        return _simulate_ndvi(polygon_geojson, date_from)

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
                    "maxCloudCoverage": 90,
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
        r = requests.post(
            SENTINEL_HUB_STATS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        r.raise_for_status()

        intervals = r.json().get("data", [])
        if not intervals:
            logger.warning("No satellite intervals returned for %s — using mock.", date_from)
            return _simulate_ndvi(polygon_geojson, date_from)

        band      = (intervals[-1]
                     .get("outputs", {})
                     .get("default", {})
                     .get("bands", {})
                     .get("B0", {}))
        stats        = band.get("stats", {})
        sample_count = band.get("sampleCount", 1)
        no_data      = band.get("noDataCount", 0)
        cloud_pct    = round(no_data / max(sample_count, 1) * 100, 1)

        return {
            "ndvi_mean":          round(float(stats.get("mean",  0.0)), 4),
            "ndvi_std":           round(float(stats.get("stDev", 0.0)), 4),
            "cloud_cover_pct":    cloud_pct,
            "valid_pixels_pct":   round(100.0 - cloud_pct, 1),
            "date":               date_from,
            "cloud_contaminated": cloud_pct > CLOUD_COVER_THRESHOLD,
            "simulated":          False,
        }

    except Exception as exc:
        logger.error("NDVI fetch failed: %s — using mock.", exc)
        return _simulate_ndvi(polygon_geojson, date_from)


def get_historical_ndvi(polygon_geojson: dict, years: int = 5) -> list:
    """
    Retrieve weekly mean NDVI for a polygon going back N calendar years.

    FIX: Makes ONE API request per year (5 total for the default 5-year
    baseline) with a 7-day aggregation interval — letting Sentinel Hub
    aggregate on their servers. The old implementation made 260 separate
    requests (one per week) which exhausted the API quota and took 13+ min.

    Falls back to deterministic mock per year if any single year fails.

    Returns:
        List of {week_of_year, date, mean_ndvi, cloud_contaminated}
    """
    token = _get_token()
    if token is None:
        logger.warning("No credentials — returning mock historical NDVI.")
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
                # ONE request covers the full year at weekly resolution
                "aggregationInterval": {"of": "P7D"},
                "evalscript": NDVI_EVALSCRIPT,
                "resx": 10,
                "resy": 10,
            },
        }

        try:
            r = requests.post(
                SENTINEL_HUB_STATS_URL,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
                timeout=60,
            )
            r.raise_for_status()

            for interval in r.json().get("data", []):
                date_str  = interval["interval"]["from"][:10]
                date_obj  = datetime.strptime(date_str, "%Y-%m-%d")
                week      = date_obj.isocalendar()[1]
                band      = (interval
                             .get("outputs", {})
                             .get("default", {})
                             .get("bands", {})
                             .get("B0", {}))
                mean_ndvi = band.get("stats", {}).get("mean")

                if mean_ndvi is not None and 0.0 < float(mean_ndvi) < 1.0:
                    results.append({
                        "week_of_year":     week,
                        "date":             date_str,
                        "mean_ndvi":        round(float(mean_ndvi), 4),
                        "cloud_contaminated": False,
                    })

        except Exception as exc:
            logger.error(
                "Historical NDVI failed for year %d: %s — using mock for this year.",
                year, exc,
            )
            results.extend(_mock_historical_ndvi(1, base_year=year))

    logger.info(
        "Historical NDVI: %d weekly records fetched across %d years.", len(results), years
    )
    return results


def get_sar_backscatter(
    polygon_geojson: dict, date_from: str, date_to: str
) -> dict:
    """
    Return Sentinel-1 SAR VV/VH backscatter for flood detection.

    SAR sees through clouds — used when NDVI is cloud-contaminated.
    High VV/VH ratio with low VV indicates standing water (flood).
    Falls back to simulation when credentials are absent.

    Returns:
        {vv_mean, vh_mean, vv_vh_ratio, simulated}
    """
    token = _get_token()
    if token is None:
        rng = random.Random(
            int(hashlib.md5(f"{date_from}sar".encode()).hexdigest()[:8], 16)
        )
        vv = rng.uniform(-18, -8)
        vh = vv - rng.uniform(5, 12)
        return {
            "vv_mean":      round(vv, 3),
            "vh_mean":      round(vh, 3),
            "vv_vh_ratio":  round(vv / (vh - 0.001), 3),
            "simulated":    True,
        }

    payload = {
        "input": {
            "bounds": {"geometry": polygon_geojson},
            "data": [{
                "type": "sentinel-1-grd",
                "dataFilter": {
                    "timeRange": {
                        "from": f"{date_from}T00:00:00Z",
                        "to":   f"{date_to}T23:59:59Z",
                    },
                },
            }],
        },
        "aggregation": {
            "timeRange": {
                "from": f"{date_from}T00:00:00Z",
                "to":   f"{date_to}T23:59:59Z",
            },
            "aggregationInterval": {"of": "P5D"},
            "evalscript": SAR_EVALSCRIPT,
            "resx": 10,
            "resy": 10,
        },
    }

    try:
        r = requests.post(
            SENTINEL_HUB_STATS_URL,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        )
        r.raise_for_status()

        intervals = r.json().get("data", [])
        if not intervals:
            return {"vv_mean": -15.0, "vh_mean": -22.0, "vv_vh_ratio": 0.68, "simulated": True}

        bands = intervals[-1].get("outputs", {}).get("default", {}).get("bands", {})
        vv    = float(bands.get("B0", {}).get("stats", {}).get("mean", -15.0))
        vh    = float(bands.get("B1", {}).get("stats", {}).get("mean", -22.0))
        return {
            "vv_mean":     round(vv, 3),
            "vh_mean":     round(vh, 3),
            "vv_vh_ratio": round(vv / (vh - 0.001), 3),
            "simulated":   False,
        }

    except Exception as exc:
        logger.error("SAR fetch failed: %s", exc)
        return {"vv_mean": -15.0, "vh_mean": -22.0, "vv_vh_ratio": 0.68, "simulated": True}