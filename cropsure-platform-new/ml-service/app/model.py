"""Stress classification model: load, predict, explain."""

import math
import os
import logging
from datetime import datetime
from typing import Optional

import joblib
import numpy as np

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "cropsure_model.pkl")
PAYOUT_CONFIDENCE_THRESHOLD = 0.72

EXPLANATIONS = {
    "no_stress": {
        "en": "Crop vegetation looks healthy. No stress indicators detected.",
        "sw": "Mimea iko vizuri. Hakuna dalili za msongo.",
    },
    "drought": {
        "en": "Drought stress detected. Vegetation health dropped {pct}% below your {month} baseline.",
        "sw": "Msongo wa ukame umegunduliwa. Afya ya mazao ilishuka {pct}% chini ya wastani wako wa {month}.",
    },
    "flood": {
        "en": "Flood stress detected. Excess water on your farm has damaged crop vegetation.",
        "sw": "Msongo wa mafuriko umegunduliwa. Maji mengi yameharibu mazao shambani kwako.",
    },
    "pest_disease": {
        "en": "Pest or disease stress detected. Unusual vegetation decline noted without weather cause.",
        "sw": "Msongo wa wadudu au ugonjwa umegunduliwa. Kupungua kwa ajabu kwa mimea bila sababu ya hali ya hewa.",
    },
}

_model_cache: Optional[dict] = None


def _seasonal_factor(day_of_year: float) -> float:
    """Sin-transformed East Africa rain cycle — matches train.py exactly."""
    return 0.15 * math.sin((day_of_year - 60) * math.pi / 182)


def _load_model() -> dict:
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    if not os.path.exists(MODEL_PATH):
        logger.warning("Model not found at %s — training now", MODEL_PATH)
        from .train import train_model
        train_model()
    _model_cache = joblib.load(MODEL_PATH)
    return _model_cache


def predict_stress(features: dict) -> dict:
    """
    Predict crop stress from a feature dict.

    Expected keys (standardised — all come from build_feature_vector()):
        ndvi_zscore            z-score vs farm personal baseline
        ndvi_roc               rate of change over last 3 readings
        rainfall_anomaly_mm    too little = drought, too much = flood
        day_of_year            1-365
        cloud_contaminated     0 or 1

    seasonal_factor is computed internally from day_of_year so it always
    matches the training formula even if the caller omits it.

    Returns: stress_type, confidence, payout_recommended, probabilities
    """
    artifact = _load_model()
    model = artifact["model"]
    label_map: dict = artifact["classes"]  # {0: "no_stress", 1: "drought", ...}

    day_of_year = float(features.get("day_of_year", 180))
    cloud = bool(features.get("cloud_contaminated", False))

    # Build the 6-column vector in the same order as train.py FEATURE_NAMES:
    # [ndvi_zscore, ndvi_roc, rainfall_anomaly_mm, day_of_year, seasonal_factor, cloud_contaminated]
    feature_vec = np.array([[
        float(features.get("ndvi_zscore", 0.0)),
        float(features.get("ndvi_roc", 0.0)),           # key must be "ndvi_roc"
        float(features.get("rainfall_anomaly_mm", 0.0)),
        day_of_year,
        _seasonal_factor(day_of_year),                   # always computed, not trusted from dict
        float(cloud),
    ]], dtype=np.float32)

    import warnings
    with warnings.catch_warnings():
        # LightGBM trained with auto-generated column names; numpy array is fine
        warnings.filterwarnings("ignore", message="X does not have valid feature names")
        proba = model.predict_proba(feature_vec)[0]
    label_idx = int(np.argmax(proba))
    confidence = float(np.max(proba))
    stress_type = label_map[label_idx]

    # Suppress payout if reading is cloud-contaminated (unreliable NDVI)
    payout_recommended = (
        stress_type != "no_stress"
        and confidence >= PAYOUT_CONFIDENCE_THRESHOLD
        and not cloud
    )

    return {
        "stress_type": stress_type,
        "confidence": round(confidence, 4),
        "payout_recommended": payout_recommended,
        "probabilities": {label_map[i]: round(float(p), 4) for i, p in enumerate(proba)},
    }


def build_explanation(stress_type: str, deviation_pct: Optional[float]) -> dict:
    """Build bilingual explanation string for SMS/WhatsApp."""
    template = EXPLANATIONS.get(stress_type, EXPLANATIONS["no_stress"])
    month = datetime.utcnow().strftime("%B")
    pct = abs(round(deviation_pct or 0, 1))
    return {
        "en": template["en"].format(pct=pct, month=month),
        "sw": template["sw"].format(pct=pct, month=month),
    }
