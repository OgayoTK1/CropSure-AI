"""
train.py — Synthetic data generation and model training
for CropSure stress classifier.

Run once:  python train.py
Output:    models/cropsure_model.pkl
           models/model_metadata.json
"""

import json
import logging
import os
from datetime import datetime

import joblib
import numpy as np
from sklearn.metrics import classification_report, accuracy_score, f1_score
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

MODEL_DIR  = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "cropsure_model.pkl")
META_PATH  = os.path.join(MODEL_DIR, "model_metadata.json")

# ── Must match exactly what model.py and utils.py send at inference ───────────
FEATURE_NAMES = [
    "ndvi_zscore",           # z-score vs farm personal baseline
    "ndvi_roc",              # rate of change over last 3 readings
    "rainfall_anomaly_mm",   # deviation from climatological normal
    "day_of_year",           # 1–365 (phenological stage)
    "seasonal_factor",       # sin-transformed East Africa rain cycle
    "cloud_contaminated",    # 0 or 1 — suppresses payout if 1
]

# ── Must match exactly what model.py's EXPLANATIONS dict uses as keys ─────────
CLASSES = {
    0: "no_stress",
    1: "drought",
    2: "flood",
    3: "pest_disease",
}


def _seasonal(doy: float) -> float:
    """Match the seasonal_factor formula in utils.py exactly."""
    import math
    return 0.15 * math.sin((doy - 60) * math.pi / 182)


def generate_training_data(n_samples: int = 3000) -> tuple:
    """
    Generate synthetic labelled training data using agronomic rules.

    Rules:
        no_stress   : NDVI near or above baseline, normal weather
        drought     : sharp NDVI drop + large rainfall deficit
        flood       : NDVI drop + large rainfall surplus
                      cloud_contaminated varies (not always 1)
        pest_disease: NDVI drop with NO weather anomaly

    day_of_year covers the full 1–365 range so the model learns
    stress patterns for every season, not just a narrow window.
    """
    rng = np.random.default_rng(42)
    records = []

    # Class distribution realistic for Kenyan farming context
    class_probs = [0.55, 0.25, 0.11, 0.09]
    labels      = rng.choice([0, 1, 2, 3], size=n_samples, p=class_probs)

    for label in labels:
        # Full year coverage — not a narrow window
        doy        = int(rng.integers(1, 366))
        seasonal   = _seasonal(doy)

        if label == 0:   # no stress
            zscore  = rng.normal(0.2,   0.6)
            roc     = rng.normal(0.005, 0.015)
            rain    = rng.normal(0,     15)
            cloud   = int(rng.random() > 0.88)   # occasional cloud, not flood-linked

        elif label == 1:  # drought
            zscore  = rng.normal(-2.2,  0.55)
            roc     = rng.normal(-0.045, 0.02)
            rain    = rng.normal(-32,   10)
            cloud   = 0                            # drought = clear skies

        elif label == 2:  # flood
            zscore  = rng.normal(-1.5,  0.6)
            roc     = rng.normal(-0.03,  0.02)
            rain    = rng.normal(+42,   14)
            # FIX: cloud varies for flood — not always 1
            cloud   = int(rng.random() > 0.45)

        else:            # pest / disease
            zscore  = rng.normal(-1.8,  0.5)
            roc     = rng.normal(-0.055, 0.025)
            rain    = rng.normal(+3,    12)        # no weather anomaly
            cloud   = 0

        records.append((
            float(np.clip(zscore, -6,    3)),
            float(np.clip(roc,    -0.25, 0.25)),
            float(np.clip(rain,   -70,   80)),
            doy,
            round(seasonal, 4),
            cloud,
            label,
        ))

    X = np.array([r[:6] for r in records], dtype=np.float32)
    y = np.array([r[6]  for r in records], dtype=np.int32)
    return X, y


def train_model():
    """Train the LightGBM classifier and save model + metadata to disk."""
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    logger.info("Generating %d synthetic training samples...", 3000)
    X, y = generate_training_data(3000)

    X_tr, X_val, y_tr, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    try:
        import lightgbm as lgb
        model = lgb.LGBMClassifier(
            n_estimators=300,
            learning_rate=0.04,
            max_depth=6,
            num_leaves=31,
            min_child_samples=15,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
        )
        model.fit(
            X_tr, y_tr,
            eval_set=[(X_val, y_val)],
            callbacks=[
                lgb.early_stopping(30, verbose=False),
                lgb.log_evaluation(period=-1),
            ],
        )
        logger.info("LightGBM training complete.")

    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        logger.warning("LightGBM not installed — using sklearn GradientBoosting.")
        model = GradientBoostingClassifier(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=5,
            random_state=42,
        )
        model.fit(X_tr, y_tr)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    y_pred  = model.predict(X_val)
    acc     = accuracy_score(y_val, y_pred)
    f1_mac  = f1_score(y_val, y_pred, average="macro")
    report  = classification_report(
        y_val, y_pred,
        target_names=list(CLASSES.values())
    )
    logger.info("Validation results:\n%s", report)
    logger.info("Accuracy: %.4f  |  Macro F1: %.4f", acc, f1_mac)

    # ── Save model artifact ───────────────────────────────────────────────────
    os.makedirs(MODEL_DIR, exist_ok=True)

    artifact = {
        "model":         model,
        "classes":       CLASSES,        # ← key matches model.py exactly
        "feature_cols":  FEATURE_NAMES,  # ← key matches model.py exactly
        "accuracy":      round(acc, 4),
        "macro_f1":      round(f1_mac, 4),
    }
    joblib.dump(artifact, MODEL_PATH)
    logger.info("Model saved → %s", MODEL_PATH)

    # ── Save metadata JSON (for dashboard and logging) ────────────────────────
    metadata = {
        "classes":          CLASSES,
        "feature_cols":     FEATURE_NAMES,
        "accuracy":         round(acc, 4),
        "macro_f1":         round(f1_mac, 4),
        "training_samples": len(X_tr),
        "eval_samples":     len(X_val),
        "trained_at":       datetime.utcnow().isoformat(),
        "data_source":      "synthetic",
    }
    with open(META_PATH, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info("Metadata saved → %s", META_PATH)

    return model


if __name__ == "__main__":
    train_model()