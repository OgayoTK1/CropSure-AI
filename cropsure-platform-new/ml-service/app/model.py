"""Stress classification model: load, predict, explain."""

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
    features keys: ndvi_zscore, ndvi_rate_of_change_3period, rainfall_anomaly_mm,
                   day_of_year, cloud_contaminated
    Returns: stress_type, confidence, payout_recommended, probabilities
    """
    artifact = _load_model()
    model = artifact["model"]
    label_map: dict = artifact["label_map"]

    feature_vec = np.array([[
        features.get("ndvi_zscore", 0.0),
        features.get("ndvi_rate_of_change_3period", 0.0),
        features.get("rainfall_anomaly_mm", 0.0),
        features.get("day_of_year", 180),
        float(features.get("cloud_contaminated", False)),
    ]], dtype=np.float32)

    label_idx = int(model.predict(feature_vec)[0])
    try:
        proba = model.predict_proba(feature_vec)[0]
        confidence = float(proba[label_idx])
        probabilities = {label_map[i]: round(float(p), 4) for i, p in enumerate(proba)}
    except AttributeError:
        confidence = 0.85
        probabilities = {v: 0.0 for v in label_map.values()}
        probabilities[label_map[label_idx]] = confidence

    stress_type = label_map[label_idx]
    payout_recommended = stress_type != "no_stress" and confidence >= PAYOUT_CONFIDENCE_THRESHOLD

    return {
        "stress_type": stress_type,
        "confidence": round(confidence, 4),
        "payout_recommended": payout_recommended,
        "probabilities": probabilities,
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
