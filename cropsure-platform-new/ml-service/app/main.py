"""CropSure ML Microservice — FastAPI app on port 8001.

Pipeline for every farm check:
  Step 1 — sentinel.py  : get_ndvi()          → today's NDVI reading
  Step 2 — baseline.py  : compute_ndvi_zscore()  → z-score vs personal baseline
             baseline.py  : ndvi_deviation_pct()  → human-readable % drop
             baseline.py  : compute_rate_of_change() → is it falling fast?
  Step 3 — utils.py     : build_feature_vector() → 6-number array for classifier
  Step 4 — model.py     : predict_stress()     → stress class + confidence
  Decision: confidence ≥ 0.72 AND not cloud_contaminated → payout fires
"""

import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .sentinel import get_ndvi, get_sar_backscatter
from .baseline import (
    build_farm_baseline,
    compute_ndvi_zscore,
    ndvi_deviation_pct,
    compute_rate_of_change,
)
from .model import predict_stress, build_explanation
from .utils import get_rainfall_anomaly, polygon_centroid, build_feature_vector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── Startup: warm the model cache so first request is fast ───────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    from .model import _load_model
    _load_model()
    logger.info("CropSure ML service ready — model loaded")
    yield


app = FastAPI(
    title="CropSure ML Service",
    version="2.0.0",
    description=(
        "Satellite NDVI analysis and per-farm crop stress classification. "
        "Uses Sentinel-2 NDVI + Sentinel-1 SAR + personal farm baseline."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    farm_id: str
    polygon_geojson: dict
    baseline_dict: dict                     # pre-built at enrollment time
    recent_ndvi_series: list[float] = []   # last 3-5 readings for rate-of-change


class BaselineRequest(BaseModel):
    farm_id: str
    polygon_geojson: dict
    years: int = 5


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ml-service",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ── Step 0: Build baseline (called once at enrollment) ───────────────────────

@app.post("/build-baseline")
def build_baseline_endpoint(req: BaselineRequest):
    """
    Fetch 5 years of weekly Sentinel-2 NDVI for the polygon and compute
    per-week mean/std.  Fired fire-and-forget by the backend after enrollment.
    Result is stored in PostgreSQL Baseline table and passed back to /analyze.
    """
    try:
        baseline = build_farm_baseline(req.polygon_geojson, years=req.years)
        return {
            "farm_id": req.farm_id,
            "baseline": baseline,
            "weeks_covered": len(baseline),
            "built_at": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.exception("Baseline build failed for farm %s", req.farm_id)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Steps 1-4: Full analysis pipeline ────────────────────────────────────────

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Full pipeline: satellite read → baseline compare → feature engineering
    → classifier → payout decision.

    Falls back to deterministic mock data at every step when Sentinel Hub
    credentials are absent — guarantees < 300 ms response for demo.
    """
    try:
        today = date.today()
        date_from = (today - timedelta(days=5)).isoformat()
        date_to = today.isoformat()

        # ── Step 1: Get today's NDVI from satellite ───────────────────────────
        ndvi_reading = get_ndvi(req.polygon_geojson, date_from, date_to)
        ndvi_current = ndvi_reading["ndvi_mean"]
        cloud_contaminated = ndvi_reading["cloud_contaminated"]

        # ── Step 2: Compare against the farm's personal baseline ──────────────
        week = today.isocalendar()[1]

        zscore = compute_ndvi_zscore(ndvi_current, week, req.baseline_dict)
        if zscore is None:
            # Baseline doesn't cover this week yet — treat as no-stress, no payout
            zscore = 0.0

        deviation = ndvi_deviation_pct(ndvi_current, week, req.baseline_dict)
        baseline_mean = req.baseline_dict.get(str(week), {}).get("mean", ndvi_current)

        # Include current reading in ROC series so we capture today's drop
        roc_series = list(req.recent_ndvi_series) + [ndvi_current]
        roc = compute_rate_of_change(roc_series)

        # ── Step 3: Build feature vector ──────────────────────────────────────
        # Rainfall anomaly uses farm centroid for location context
        lat, lon = polygon_centroid(req.polygon_geojson)
        rain_anomaly = get_rainfall_anomaly(lat, lon, today.isoformat())

        features = build_feature_vector(
            ndvi_zscore=zscore,
            ndvi_roc=roc,
            rainfall_anomaly_mm=rain_anomaly,
            dt=today,
            cloud_contaminated=cloud_contaminated,
        )

        # ── Step 4: Run classifier ────────────────────────────────────────────
        result = predict_stress(features)
        explanation = build_explanation(result["stress_type"], deviation)

        # SAR backscatter for flood/drought differentiation (supplementary)
        sar = get_sar_backscatter(req.polygon_geojson, date_from, date_to)

        return {
            "farm_id": req.farm_id,
            # Satellite reading
            "ndvi_current": ndvi_current,
            "ndvi_baseline_mean": round(float(baseline_mean), 4),
            "ndvi_deviation_pct": deviation,
            "ndvi_zscore": zscore,
            "ndvi_roc": roc,
            # Classifier output
            "stress_type": result["stress_type"],
            "confidence": result["confidence"],
            "payout_recommended": result["payout_recommended"],
            "probabilities": result["probabilities"],
            # Context
            "rainfall_anomaly_mm": rain_anomaly,
            "cloud_contaminated": cloud_contaminated,
            "sar": sar,
            # Bilingual explanation for SMS/WhatsApp
            "explanation_en": explanation["en"],
            "explanation_sw": explanation["sw"],
            "analyzed_at": datetime.utcnow().isoformat(),
            "feature_vector": features,   # logged for model audit trail
        }

    except Exception as exc:
        logger.exception("Analysis failed for farm %s", req.farm_id)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Demo: force a drought result (hackathon pitch button) ────────────────────

@app.post("/simulate-drought/{farm_id}")
def simulate_drought_endpoint(farm_id: str, polygon_geojson: dict = None):
    """
    Return a pre-baked drought result without calling Sentinel Hub.
    Used by the demo 'Trigger Drought Event' button on stage.
    Fires the real notification pipeline — only the satellite read is faked.
    """
    explanation = build_explanation("drought", -31.5)
    return {
        "farm_id": farm_id,
        "stress_type": "drought",
        "confidence": 0.91,
        "payout_recommended": True,
        "ndvi_current": 0.28,
        "ndvi_baseline_mean": 0.62,
        "ndvi_deviation_pct": -31.5,
        "ndvi_zscore": -2.4,
        "ndvi_roc": -0.062,
        "rainfall_anomaly_mm": -38.0,
        "cloud_contaminated": False,
        "probabilities": {
            "no_stress": 0.03,
            "drought": 0.91,
            "flood": 0.04,
            "pest_disease": 0.02,
        },
        "explanation_en": explanation["en"],
        "explanation_sw": explanation["sw"],
        "analyzed_at": datetime.utcnow().isoformat(),
        "simulated": True,
    }
