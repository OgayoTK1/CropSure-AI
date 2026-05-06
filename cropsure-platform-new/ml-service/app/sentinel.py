"""Sentinel Hub integration for NDVI and SAR data retrieval."""

import os
import logging
import math
import random
from datetime import datetime, timedelta
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

SENTINEL_HUB_TOKEN_URL = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
SENTINEL_HUB_STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"

NDVI_EVALSCRIPT = """
//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B04","B08","SCL"], units:"DN" }],
    output: [{ id:"default", bands:1, sampleType:"FLOAT32" }],
    mosaicking: "ORBIT"
  };
}
function evaluatePixel(samples) {
  if ([3,8,9,10].includes(samples.SCL)) return [NaN];
  return [(samples.B08 - samples.B04) / (samples.B08 + samples.B04 + 1e-6)];
}
"""

SAR_EVALSCRIPT = """
//VERSION=3
function setup() {
  return { input:[{bands:["VV","VH"]}], output:[{id:"default",bands:2,sampleType:"FLOAT32"}], mosaicking:"ORBIT" };
}
function evaluatePixel(s) { return [s.VV, s.VH]; }
"""


def _get_token() -> Optional[str]:
    cid = os.getenv("SENTINEL_HUB_CLIENT_ID", "")
    csec = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")
    if not cid or not csec:
        return None
    try:
        r = requests.post(
            SENTINEL_HUB_TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=HTTPBasicAuth(cid, csec),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()["access_token"]
    except Exception as e:
        logger.error("Sentinel Hub token error: %s", e)
        return None


def _simulate_ndvi(date_from: str) -> dict:
    try:
        d = datetime.strptime(date_from, "%Y-%m-%d")
    except Exception:
        d = datetime.utcnow()
    week = d.isocalendar()[1]
    seasonal = 0.55 + 0.25 * math.sin(2 * math.pi * week / 52)
    ndvi = max(0.1, min(0.95, seasonal + random.gauss(0, 0.03)))
    cloud = random.uniform(5, 25)
    return {
        "ndvi_mean": round(ndvi, 4),
        "ndvi_std": round(abs(random.gauss(0, 0.02)), 4),
        "cloud_cover_pct": round(cloud, 1),
        "valid_pixels_pct": round(100 - cloud, 1),
        "date": date_from,
        "cloud_contaminated": cloud > 60,
        "simulated": True,
    }


def get_ndvi(polygon_geojson: dict, date_from: str, date_to: str) -> dict:
    """Return mean NDVI for a farm polygon. Falls back to simulation if no credentials."""
    token = _get_token()
    if token is None:
        return _simulate_ndvi(date_from)

    payload = {
        "input": {
            "bounds": {"geometry": polygon_geojson},
            "data": [{
                "type": "sentinel-2-l2a",
                "dataFilter": {
                    "timeRange": {"from": f"{date_from}T00:00:00Z", "to": f"{date_to}T23:59:59Z"},
                    "maxCloudCoverage": 90,
                },
            }],
        },
        "aggregation": {
            "timeRange": {"from": f"{date_from}T00:00:00Z", "to": f"{date_to}T23:59:59Z"},
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
            return _simulate_ndvi(date_from)
        stats = intervals[-1].get("outputs", {}).get("default", {}).get("bands", {}).get("B0", {}).get("stats", {})
        sample_count = intervals[-1].get("outputs", {}).get("default", {}).get("bands", {}).get("B0", {}).get("sampleCount", 1)
        no_data = intervals[-1].get("outputs", {}).get("default", {}).get("bands", {}).get("B0", {}).get("noDataCount", 0)
        cloud_pct = round(no_data / max(sample_count, 1) * 100, 1)
        return {
            "ndvi_mean": round(float(stats.get("mean", 0.0)), 4),
            "ndvi_std": round(float(stats.get("stDev", 0.0)), 4),
            "cloud_cover_pct": cloud_pct,
            "valid_pixels_pct": round(100 - cloud_pct, 1),
            "date": date_from,
            "cloud_contaminated": cloud_pct > 60,
            "simulated": False,
        }
    except Exception as e:
        logger.error("NDVI fetch failed: %s — using simulation", e)
        return _simulate_ndvi(date_from)


def get_historical_ndvi(polygon_geojson: dict, years: int = 5) -> list:
    """Return weekly mean NDVI list over past N years for baseline building."""
    end = datetime.utcnow()
    start = end - timedelta(days=365 * years)
    results = []
    cursor = start
    while cursor < end:
        w_end = min(cursor + timedelta(days=6), end)
        reading = get_ndvi(
            polygon_geojson,
            cursor.strftime("%Y-%m-%d"),
            w_end.strftime("%Y-%m-%d"),
        )
        results.append({
            "week_of_year": cursor.isocalendar()[1],
            "date": cursor.strftime("%Y-%m-%d"),
            "mean_ndvi": reading["ndvi_mean"],
            "cloud_contaminated": reading["cloud_contaminated"],
        })
        cursor = w_end + timedelta(days=1)
    return results


def get_sar_backscatter(polygon_geojson: dict, date_from: str, date_to: str) -> dict:
    """Return Sentinel-1 SAR VV/VH for flood detection. Simulated when no credentials."""
    token = _get_token()
    if token is None:
        vv = random.uniform(-18, -8)
        vh = vv - random.uniform(5, 12)
        return {"vv_mean": round(vv, 3), "vh_mean": round(vh, 3), "vv_vh_ratio": round(vv / (vh - 0.001), 3), "simulated": True}

    payload = {
        "input": {
            "bounds": {"geometry": polygon_geojson},
            "data": [{
                "type": "sentinel-1-grd",
                "dataFilter": {
                    "timeRange": {"from": f"{date_from}T00:00:00Z", "to": f"{date_to}T23:59:59Z"},
                },
            }],
        },
        "aggregation": {
            "timeRange": {"from": f"{date_from}T00:00:00Z", "to": f"{date_to}T23:59:59Z"},
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
        vv = float(bands.get("B0", {}).get("stats", {}).get("mean", -15.0))
        vh = float(bands.get("B1", {}).get("stats", {}).get("mean", -22.0))
        return {"vv_mean": round(vv, 3), "vh_mean": round(vh, 3), "vv_vh_ratio": round(vv / (vh - 0.001), 3), "simulated": False}
    except Exception as e:
        logger.error("SAR fetch failed: %s", e)
        return {"vv_mean": -15.0, "vh_mean": -22.0, "vv_vh_ratio": 0.68, "simulated": True}
