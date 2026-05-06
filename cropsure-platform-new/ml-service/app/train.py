"""Synthetic data generation and model training for CropSure stress classifier."""

import os
import random
import logging
import numpy as np
import joblib

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "cropsure_model.pkl")
LABEL_MAP = {0: "no_stress", 1: "drought", 2: "flood", 3: "pest_disease"}
FEATURE_NAMES = ["ndvi_zscore", "ndvi_rate_of_change_3period", "rainfall_anomaly_mm", "day_of_year", "cloud_contaminated"]


def generate_training_data(n_samples: int = 3000):
    rng = random.Random(42)
    np.random.seed(42)
    X, y = [], []

    def add(zscore, roc, rain, doy, cloud, label, n, noise=0.15):
        for _ in range(n):
            X.append([
                zscore + rng.gauss(0, noise),
                roc + rng.gauss(0, 0.05),
                rain + rng.gauss(0, 8),
                doy + rng.randint(-15, 15),
                float(cloud),
            ])
            y.append(label)

    per = n_samples // 4
    add(0.1, 0.02, 0, 150, 0, 0, per)       # no stress
    add(-2.2, -0.08, -35, 160, 0, 1, per)   # drought
    add(-1.3, -0.05, 55, 120, 1, 2, per)    # flood
    add(-1.0, -0.04, 5, 180, 0, 3, per)     # pest/disease

    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32)


def train_model():
    X, y = generate_training_data()
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report
    X_tr, X_val, y_tr, y_val = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    try:
        import lightgbm as lgb
        model = lgb.LGBMClassifier(
            n_estimators=200, learning_rate=0.05, max_depth=6,
            num_leaves=31, class_weight="balanced", random_state=42, verbose=-1,
        )
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(n_estimators=200, learning_rate=0.05, max_depth=5, random_state=42)
        logger.warning("LightGBM unavailable — using sklearn GradientBoosting")

    model.fit(X_tr, y_tr)
    report = classification_report(y_val, model.predict(X_val), target_names=list(LABEL_MAP.values()))
    logger.info("Validation:\n%s", report)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "label_map": LABEL_MAP, "feature_names": FEATURE_NAMES}, MODEL_PATH)
    logger.info("Model saved → %s", MODEL_PATH)
    return model


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_model()
