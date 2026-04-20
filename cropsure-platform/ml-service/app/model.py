"""
model.py — Stress prediction inference for CropSure AI.

Loads the trained LightGBM model and exposes a single predict_stress()
function.  Auto-trains the model on first call if the pkl file is absent
(useful in fresh container starts).

Author: CropSure ML Team (Member 1)
"""

import os
import math
import logging
from datetime import datetime
from typing import Optional

import numpy as np
import joblib

logger = logging.getLogger(__name__)

MODEL_PATH        = os.path.join(os.path.dirname(__file__), "models", "cropsure_model.pkl")
PAYOUT_THRESHOLD  = 0.72   # minimum confidence to recommend a payout

# Bilingual explanation templates keyed by stress_type
EXPLANATIONS: dict = {
    "no_stress": {
        "en": "Your crops are healthy. No stress detected this week.",
        "sw": "Mazao yako yako sawa. Hakuna msongo ulioonekana wiki hii.",
    },
    "drought": {
        "en": (
            "Drought stress detected. Vegetation health dropped {pct}% below your "
            "{month} baseline. Payout of KES {amount} has been sent to your M-Pesa."
        ),
        "sw": (
            "Msongo wa ukame umegunduliwa. Afya ya mazao ilishuka asilimia {pct} "
            "chini ya wastani wako wa {month_sw}. "
            "Malipo ya KES {amount} yametumwa kwa M-Pesa yako."
        ),
    },
    "flood": {
        "en": (
            "Flood stress detected. Excess water on your farm dropped vegetation "
            "health {pct}% below your {month} baseline. Payout triggered."
        ),
        "sw": (
            "Msongo wa mafuriko umegunduliwa. Maji mengi shambani kwako "
            "yalisababisha afya ya mazao kushuka asilimia {pct}. Malipo yameanzishwa."
        ),
    },
    "pest_disease": {
        "en": (
            "Pest or disease stress detected. Crop health declined {pct}% without a "
            "weather cause — this pattern matches pest or disease damage. Payout triggered."
        ),
        "sw": (
            "Msongo wa wadudu au ugonjwa umegunduliwa. Afya ya mazao ilishuka "
            "asilimia {pct} bila sababu ya hali ya hewa. Malipo yameanzishwa."
        ),
    },
}

MONTH_SW = {
    1:"Januari", 2:"Februari", 3:"Machi", 4:"Aprili", 5:"Mei", 6:"Juni",
    7:"Julai", 8:"Agosti", 9:"Septemba", 10:"Oktoba", 11:"Novemba", 12:"Desemba",
}

# ── Model cache (loaded once per process) ─────────────────────────────────────
_artifact: Optional[dict] = None


def _load_model() -> dict:
    """Load the model artifact, training it first if the pkl is missing."""
    global _artifact
    if _artifact is not None:
        return _artifact

    if not os.path.exists(MODEL_PATH):
        logger.warning("Model file not found at %s — training now...", MODEL_PATH)
        from train import train_model
        train_model()

    _artifact = joblib.load(MODEL_PATH)
    logger.info(
        "Model loaded — classes: %s, accuracy: %.3f",
        list(_artifact["classes"].values()),
        _artifact.get("accuracy", 0.0),
    )
    return _artifact


def predict_stress(
    ndvi_zscore:          float,
    ndvi_roc:             float,
    rainfall_anomaly_mm:  float,
    day_of_year:          int,
    cloud_contaminated:   bool  = False,
    ndvi_deviation_pct:   float = 0.0,
    payout_amount_kes:    float = 0.0,
) -> dict:
    """
    Predict crop stress type and generate a payout recommendation.

    Args:
        ndvi_zscore          : standard deviations below the farm's personal baseline
        ndvi_roc             : mean NDVI change per 5-day period (last 3 readings)
        rainfall_anomaly_mm  : mm deviation from climatological normal
        day_of_year          : 1–365
        cloud_contaminated   : True if cloud cover > 60 % (reduces confidence)
        ndvi_deviation_pct   : human-readable % deviation (for notification text)
        payout_amount_kes    : expected payout amount (for notification text)

    Returns:
        {
            stress_type          str   "no_stress" | "drought" | "flood" | "pest_disease"
            confidence           float 0.0 – 1.0
            payout_recommended   bool  True when stress detected + confidence ≥ 0.72
            class_probabilities  dict  {class_name: probability}
            explanation_en       str   English notification text
            explanation_sw       str   Swahili notification text
            cloud_contaminated   bool
        }
    """
    artifact  = _load_model()
    model     = artifact["model"]
    feat_cols = artifact["feature_cols"]
    classes   = artifact["classes"]

    seasonal_factor = 0.15 * math.sin((day_of_year - 60) * math.pi / 182)

    features = np.array([[
        ndvi_zscore,
        ndvi_roc,
        rainfall_anomaly_mm,
        day_of_year,
        seasonal_factor,
        int(cloud_contaminated),
    ]], dtype=float)

    proba           = model.predict_proba(features)[0]
    predicted_class = int(np.argmax(proba))
    confidence      = float(np.max(proba))
    stress_type     = classes[predicted_class]

    # Dampen confidence on cloud-contaminated readings to reduce false triggers
    if cloud_contaminated and stress_type != "no_stress":
        confidence = min(confidence, 0.60)

    payout_recommended = (
        stress_type != "no_stress"
        and confidence >= PAYOUT_THRESHOLD
        and not cloud_contaminated
    )

    # Build bilingual explanation with dynamic values
    now       = datetime.utcnow()
    month_en  = now.strftime("%B")
    month_sw  = MONTH_SW.get(now.month, month_en)
    pct_abs   = abs(round(ndvi_deviation_pct, 1))
    amount    = f"{int(payout_amount_kes):,}"

    tmpl = EXPLANATIONS.get(stress_type, EXPLANATIONS["no_stress"])
    explanation_en = tmpl["en"].format(pct=pct_abs, month=month_en, amount=amount)
    explanation_sw = tmpl["sw"].format(pct=pct_abs, month_sw=month_sw, amount=amount)

    return {
        "stress_type":         stress_type,
        "confidence":          round(confidence, 4),
        "payout_recommended":  payout_recommended,
        "class_probabilities": {classes[i]: round(float(p), 4) for i, p in enumerate(proba)},
        "explanation_en":      explanation_en,
        "explanation_sw":      explanation_sw,
        "cloud_contaminated":  cloud_contaminated,
    }
