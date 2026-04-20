"""
train.py — LightGBM stress classifier training for CropSure AI.

Run once at container startup (via Dockerfile CMD chain) to produce
models/cropsure_model.pkl.  Uses synthetic data that encodes agronomic
rules for drought, flood, and pest/disease stress signatures.

Author: CropSure ML Team (Member 1)
"""

import os
import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import lightgbm as lgb
import joblib

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODEL_DIR  = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "cropsure_model.pkl")

# Class labels
CLASSES = {
    0: "no_stress",
    1: "drought",
    2: "flood",
    3: "pest_disease",
}

FEATURE_COLS = [
    "ndvi_zscore",          # how far below personal baseline (negative = stressed)
    "ndvi_roc",             # rate of change over last 3 readings
    "rainfall_anomaly_mm",  # deviation from climatological normal (ERA5 / Open-Meteo)
    "day_of_year",          # phenological stage context
    "seasonal_factor",      # sin-transformed seasonal signal
    "cloud_contaminated",   # 0/1 — flag noisy readings
]


def generate_training_data(n_samples: int = 3000, seed: int = 42) -> pd.DataFrame:
    """
    Generate synthetic labelled training data using agronomic rules.

    Rules derived from NDVI stress literature (NASA, KALRO, ACRE Africa):
        drought     : sharp NDVI drop + significant rainfall deficit
        flood       : moderate NDVI drop + large rainfall surplus + high cloud cover
        pest/disease: moderate NDVI drop with NO weather anomaly
        no_stress   : NDVI near or above baseline, normal weather
    """
    rng     = np.random.default_rng(seed)
    records = []

    # Class distribution: realistic for Kenyan smallholder context
    class_probs = [0.55, 0.25, 0.11, 0.09]
    labels      = rng.choice([0, 1, 2, 3], size=n_samples, p=class_probs)

    for label in labels:
        day_of_year    = int(rng.integers(1, 365))
        seasonal_factor = 0.15 * np.sin((day_of_year - 60) * np.pi / 182)

        if label == 0:  # no stress
            ndvi_zscore         = rng.normal(0.2,  0.6)
            ndvi_roc            = rng.normal(0.005, 0.015)
            rainfall_anomaly_mm = rng.normal(0,    15)
            cloud_contaminated  = int(rng.random() > 0.85)

        elif label == 1:  # drought
            ndvi_zscore         = rng.normal(-2.2,  0.55)
            ndvi_roc            = rng.normal(-0.045, 0.02)
            rainfall_anomaly_mm = rng.normal(-30,   10)
            cloud_contaminated  = 0

        elif label == 2:  # flood
            ndvi_zscore         = rng.normal(-1.5,  0.6)
            ndvi_roc            = rng.normal(-0.03,  0.02)
            rainfall_anomaly_mm = rng.normal(+42,   14)
            cloud_contaminated  = int(rng.random() > 0.45)

        else:  # pest / disease
            ndvi_zscore         = rng.normal(-1.8,  0.5)
            ndvi_roc            = rng.normal(-0.055, 0.025)
            rainfall_anomaly_mm = rng.normal(+3,    12)
            cloud_contaminated  = 0

        records.append({
            "ndvi_zscore":          float(np.clip(ndvi_zscore,          -6,    3)),
            "ndvi_roc":             float(np.clip(ndvi_roc,             -0.25, 0.25)),
            "rainfall_anomaly_mm":  float(np.clip(rainfall_anomaly_mm, -70,   80)),
            "day_of_year":          day_of_year,
            "seasonal_factor":      float(seasonal_factor),
            "cloud_contaminated":   cloud_contaminated,
            "label":                label,
        })

    return pd.DataFrame(records)


def train_model(n_samples: int = 3000) -> None:
    """Train the classifier and persist it to MODEL_PATH."""
    os.makedirs(MODEL_DIR, exist_ok=True)

    logger.info("Generating %d synthetic training samples...", n_samples)
    df = generate_training_data(n_samples)

    X = df[FEATURE_COLS]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info("Training LightGBM classifier...")
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
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(period=-1)],
    )

    y_pred = model.predict(X_test)
    acc    = accuracy_score(y_test, y_pred)
    logger.info("Test accuracy: %.3f", acc)
    logger.info("\n%s", classification_report(y_test, y_pred, target_names=list(CLASSES.values())))

    artifact = {
        "model":        model,
        "feature_cols": FEATURE_COLS,
        "classes":      CLASSES,
        "accuracy":     acc,
    }
    joblib.dump(artifact, MODEL_PATH)
    logger.info("Model saved → %s", MODEL_PATH)


if __name__ == "__main__":
    train_model()
