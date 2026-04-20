"""
main.py — CropSure AI ML Microservice  (port 8001)

Exposes three endpoints:
    POST /build-baseline  — build a farm's personal NDVI fingerprint
    POST /analyze         — detect crop stress + recommend payout
    GET  /health          — liveness check

All satellite I/O is handled by sentinel.py.  Baseline maths live in
baseline.py.  ML inference lives in model.py.

Author: CropSure ML Team (Member 1)
"""

import logging
import math
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from sentinel  import get_ndvi
from baseline  import (
    build_farm_baseline,
    compute_ndvi_zscore,
    compute_ndvi_deviation_pct,
    compute_rate_of_change,
)
from model import predict_stress

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s %(levelname)-8s %(message)s",
)
logger = logging.getLogger(__name__)


# ── App lifecycle: warm the model on startup ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ML service starting — warming model cache...")
    from model import _load_model
    _load_model()
    logger.info("Model ready. ML service is live on port 8001.")
    yield
    logger.info("ML service shutting down.")


# ── FastAPI app ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="CropSure ML Service",
    description=(
        "Sentinel-2 NDVI pipeline + LightGBM crop stress classifier.\n\n"
        "Per-farm precision — compares each farm's NDVI against its own "
        "historical baseline, not a regional average."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ───────────────────────────────────────────────────────────

class BaselineRequest(BaseModel):
    farm_id:         str
    polygon_geojson: dict = Field(..., description="GeoJSON Polygon geometry")
    years:           int  = Field(5, ge=1, le=10)


class AnalyzeRequest(BaseModel):
    farm_id:              str
    polygon_geojson:      dict  = Field(..., description="GeoJSON Polygon geometry")
    baseline_dict:        Optional[dict]  = Field(None, description="Pre-built baseline; fetched fresh if absent")
    recent_ndvi_history:  Optional[list]  = Field(None, description="Last 3 NDVI readings for rate-of-change (oldest first)")
    expected_payout_kes:  Optional[float] = Field(0.0,  description="Coverage payout amount (for notification text)")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health", tags=["ops"])
def health():
    """Liveness check — returns {status: ok}."""
    return {"status": "ok", "service": "cropsure-ml"}


@app.get("/", tags=["ops"])
def root():
    return {
        "service": "CropSure ML Service",
        "version": "1.0.0",
        "docs":    "/docs",
        "health":  "/health",
        "endpoints": [
            "POST /build-baseline",
            "POST /analyze",
            "POST /analyze/simulate-drought",
        ],
    }


@app.post("/build-baseline", tags=["ml"])
async def build_baseline_endpoint(req: BaselineRequest):
    """
    Build a farm's personal NDVI baseline from satellite history.

    Call once at farm enrollment.  The returned baseline dict should be
    stored by the backend and passed back on every /analyze call to avoid
    re-fetching 5 years of satellite data.

    Response time: 5–30 s (real satellite API) | < 1 s (mock / cached)
    """
    logger.info("Building baseline for farm %s", req.farm_id)
    try:
        baseline = build_farm_baseline(req.polygon_geojson, years=req.years)
        return {
            "farm_id":      req.farm_id,
            "baseline":     baseline,
            "weeks_covered": len(baseline),
            "years_used":   req.years,
        }
    except Exception as exc:
        logger.exception("Baseline build failed for farm %s", req.farm_id)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/analyze", tags=["ml"])
async def analyze_endpoint(req: AnalyzeRequest):
    """
    Analyze current crop stress for a farm polygon.

    Pipeline:
        1. Fetch latest Sentinel-2 NDVI for the polygon (or use mock)
        2. Compute z-score against the farm's personal baseline
        3. Compute rate-of-change from recent readings
        4. Run LightGBM stress classifier
        5. Return stress type, confidence, payout recommendation,
           and bilingual explanation text

    Target response time: < 3 s (with mock/cached NDVI)
    """
    logger.info("Analyzing farm %s", req.farm_id)

    # ── 1. Fetch current NDVI (5-day window ending today) ─────────────────
    today     = date.today()
    date_to   = today.isoformat()
    date_from = (today - timedelta(days=5)).isoformat()

    try:
        ndvi_data = get_ndvi(req.polygon_geojson, date_from, date_to)
    except Exception as exc:
        logger.error("Satellite data fetch failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Satellite fetch failed: {exc}")

    # ── 2. Build baseline if not provided ─────────────────────────────────
    baseline = req.baseline_dict
    if not baseline:
        logger.info("No baseline provided — building fresh for farm %s", req.farm_id)
        baseline = build_farm_baseline(req.polygon_geojson)

    # ── 3. Compute deviation metrics ──────────────────────────────────────
    week_of_year     = today.isocalendar()[1]
    day_of_year      = today.timetuple().tm_yday
    ndvi_current     = ndvi_data["ndvi_mean"]
    ndvi_zscore      = compute_ndvi_zscore(ndvi_current, week_of_year, baseline)
    ndvi_deviation   = compute_ndvi_deviation_pct(ndvi_current, week_of_year, baseline)
    ndvi_roc         = compute_rate_of_change(req.recent_ndvi_history or [ndvi_current])
    baseline_mean    = baseline.get(str(week_of_year), {}).get("mean", 0.55)

    # Estimate rainfall anomaly from NDVI z-score as proxy
    # (real implementation would call Open-Meteo ERA5 API)
    rainfall_anomaly = _estimate_rainfall_anomaly(ndvi_zscore)

    # ── 4. Run classifier ─────────────────────────────────────────────────
    prediction = predict_stress(
        ndvi_zscore=ndvi_zscore,
        ndvi_roc=ndvi_roc,
        rainfall_anomaly_mm=rainfall_anomaly,
        day_of_year=day_of_year,
        cloud_contaminated=ndvi_data["cloud_contaminated"],
        ndvi_deviation_pct=ndvi_deviation,
        payout_amount_kes=req.expected_payout_kes or 0.0,
    )

    # ── 5. Build response ─────────────────────────────────────────────────
    return {
        "farm_id":            req.farm_id,
        "analysis_date":      today.isoformat(),
        "ndvi_current":       ndvi_current,
        "ndvi_baseline_mean": baseline_mean,
        "ndvi_deviation_pct": ndvi_deviation,
        "ndvi_zscore":        ndvi_zscore,
        "ndvi_roc":           ndvi_roc,
        "cloud_cover_pct":    ndvi_data["cloud_cover_pct"],
        "valid_pixels_pct":   ndvi_data["valid_pixels_pct"],
        **prediction,
    }


@app.post("/analyze/simulate-drought", tags=["demo"])
async def simulate_drought(req: AnalyzeRequest):
    """
    DEMO MODE — Force a drought stress result for the live pitch demo.

    Injects a synthetic NDVI 35 % below baseline and runs the full
    pipeline so the real M-Pesa notification fires on stage.
    """
    logger.info("DEMO: simulating drought for farm %s", req.farm_id)

    today        = date.today()
    week         = today.isocalendar()[1]
    baseline     = req.baseline_dict or {}
    baseline_mean= baseline.get(str(week), {}).get("mean", 0.62)
    simulated    = round(baseline_mean * 0.65, 4)

    prediction = predict_stress(
        ndvi_zscore=-2.6,
        ndvi_roc=-0.065,
        rainfall_anomaly_mm=-35.0,
        day_of_year=today.timetuple().tm_yday,
        cloud_contaminated=False,
        ndvi_deviation_pct=-35.0,
        payout_amount_kes=req.expected_payout_kes or 0.0,
    )
    # Force drought classification regardless of model output
    prediction["stress_type"]        = "drought"
    prediction["confidence"]         = 0.93
    prediction["payout_recommended"] = True

    return {
        "farm_id":            req.farm_id,
        "analysis_date":      today.isoformat(),
        "ndvi_current":       simulated,
        "ndvi_baseline_mean": baseline_mean,
        "ndvi_deviation_pct": -35.0,
        "ndvi_zscore":        -2.6,
        "ndvi_roc":           -0.065,
        "cloud_cover_pct":    8.0,
        "valid_pixels_pct":   96.0,
        "demo_mode":          True,
        **prediction,
    }


# ── Utilities ─────────────────────────────────────────────────────────────────

def _estimate_rainfall_anomaly(ndvi_zscore: float) -> float:
    """
    Rough proxy for rainfall anomaly derived from NDVI z-score.

    In production this would be replaced by an Open-Meteo / ERA5 API call
    that fetches actual accumulated rainfall vs climatological normal.
    For the hackathon demo, this heuristic is sufficient to drive the
    classifier toward the correct stress class.
    """
    if ndvi_zscore < -1.5:
        return -30.0 + ndvi_zscore * 8   # drought: large deficit
    if ndvi_zscore < -0.8:
        return -10.0                       # mild stress
    return 5.0                             # normal or positive
