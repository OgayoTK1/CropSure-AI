"""CropSure ML Microservice — FastAPI app on port 8001."""

import logging
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .sentinel import get_ndvi, get_sar_backscatter
from .baseline import build_farm_baseline, compute_ndvi_zscore, ndvi_deviation_pct
from .model import predict_stress, build_explanation
from .utils import get_rainfall_anomaly, compute_rate_of_change, polygon_centroid

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure model is trained/loaded at startup
    from .model import _load_model
    _load_model()
    logger.info("ML service ready")
    yield


app = FastAPI(
    title="CropSure ML Service",
    version="1.0.0",
    description="Satellite NDVI analysis and crop stress classification for CropSure AI",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    farm_id: str
    polygon_geojson: dict
    baseline_dict: dict
    recent_ndvi_series: list[float] = []  # last 3-5 readings for rate-of-change

class BaselineRequest(BaseModel):
    farm_id: str
    polygon_geojson: dict
    years: int = 5


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "ml-service", "timestamp": datetime.utcnow().isoformat()}


@app.post("/build-baseline")
def build_baseline(req: BaselineRequest):
    """
    Build per-farm NDVI baseline from historical Sentinel-2 data.
    Fire-and-forget from backend on enrollment.
    """
    try:
        baseline = build_farm_baseline(req.polygon_geojson, years=req.years)
        return {
            "farm_id": req.farm_id,
            "baseline": baseline,
            "weeks_covered": len(baseline),
            "built_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.exception("Baseline build failed for farm %s", req.farm_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """
    Fetch current NDVI, compute z-score, classify stress, return payout recommendation.
    Must respond in < 3 seconds for demo; simulation path ensures this.
    """
    try:
        today = datetime.utcnow()
        date_from = (today - timedelta(days=5)).strftime("%Y-%m-%d")
        date_to = today.strftime("%Y-%m-%d")

        ndvi_reading = get_ndvi(req.polygon_geojson, date_from, date_to)
        ndvi_current = ndvi_reading["ndvi_mean"]
        cloud_contaminated = ndvi_reading["cloud_contaminated"]

        week = today.isocalendar()[1]
        zscore = compute_ndvi_zscore(ndvi_current, week, req.baseline_dict) or 0.0
        dev_pct = ndvi_deviation_pct(ndvi_current, week, req.baseline_dict)

        baseline_mean = req.baseline_dict.get(str(week), {}).get("mean", ndvi_current)

        series = req.recent_ndvi_series + [ndvi_current]
        roc = compute_rate_of_change(series)

        lat, lon = polygon_centroid(req.polygon_geojson)
        rain_anomaly = get_rainfall_anomaly(lat, lon, today.strftime("%Y-%m-%d"))

        sar = get_sar_backscatter(req.polygon_geojson, date_from, date_to)

        features = {
            "ndvi_zscore": zscore,
            "ndvi_rate_of_change_3period": roc,
            "rainfall_anomaly_mm": rain_anomaly,
            "day_of_year": today.timetuple().tm_yday,
            "cloud_contaminated": cloud_contaminated,
        }

        result = predict_stress(features)
        explanation = build_explanation(result["stress_type"], dev_pct)

        return {
            "farm_id": req.farm_id,
            "stress_type": result["stress_type"],
            "confidence": result["confidence"],
            "payout_recommended": result["payout_recommended"],
            "probabilities": result["probabilities"],
            "ndvi_current": ndvi_current,
            "ndvi_baseline_mean": round(baseline_mean, 4),
            "ndvi_deviation_pct": dev_pct,
            "ndvi_zscore": zscore,
            "rainfall_anomaly_mm": rain_anomaly,
            "cloud_contaminated": cloud_contaminated,
            "sar": sar,
            "explanation_en": explanation["en"],
            "explanation_sw": explanation["sw"],
            "analyzed_at": today.isoformat(),
        }
    except Exception as e:
        logger.exception("Analysis failed for farm %s", req.farm_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/simulate-drought/{farm_id}")
def simulate_drought(farm_id: str, polygon_geojson: dict):
    """Force a drought result — used in demo pipeline."""
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
        "explanation_en": explanation["en"],
        "explanation_sw": explanation["sw"],
        "analyzed_at": datetime.utcnow().isoformat(),
        "simulated": True,
    }
