"""
test_model.py — Unit and integration tests for CropSure AI ML Service.

Tests cover:
    - GeoJSON polygon validation and area calculation
    - Sentinel Hub mock NDVI generation
    - Baseline builder correctness
    - Model inference (synthetic model fallback)
    - Feature vector construction
    - FastAPI endpoint responses

Run with:
    pytest ml-service/tests/test_model.py -v

Or from inside the container:
    docker-compose exec ml-service pytest tests/test_model.py -v

Author: CropSure ML Team (Member 1)
"""

import sys
import os
import math
import pytest
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

# Add app directory to path so imports work from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from utils import (
    validate_polygon,
    polygon_area_acres,
    polygon_centroid,
    is_valid_ndvi,
    clamp_ndvi,
    ndvi_health_label,
    ndvi_health_color,
    compute_payout_amount,
    build_feature_vector,
    week_of_year,
    day_of_year,
    month_name_en,
    month_name_sw,
)
from baseline import (
    build_farm_baseline,
    compute_ndvi_zscore,
    compute_ndvi_deviation_pct,
    compute_rate_of_change,
)
from sentinel import _mock_ndvi, _mock_historical_ndvi
from model import predict_stress


# ── Test fixtures ──────────────────────────────────────────────────────────────

# A realistic 2-acre farm polygon near Nyeri, Kenya
VALID_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [36.9400, -0.4200],
        [36.9430, -0.4200],
        [36.9430, -0.4175],
        [36.9400, -0.4175],
        [36.9400, -0.4200],
    ]]
}

# A drought scenario feature set
DROUGHT_FEATURES = {
    "ndvi_zscore":         -2.6,
    "ndvi_roc":            -0.065,
    "rainfall_anomaly_mm": -35.0,
    "day_of_year":         140,
    "seasonal_factor":     0.12,
    "cloud_contaminated":  0,
}

# A healthy crop feature set
HEALTHY_FEATURES = {
    "ndvi_zscore":         0.3,
    "ndvi_roc":            0.01,
    "rainfall_anomaly_mm": 5.0,
    "day_of_year":         120,
    "seasonal_factor":     0.10,
    "cloud_contaminated":  0,
}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — utils.py tests
# ══════════════════════════════════════════════════════════════════════════════

class TestValidatePolygon:

    def test_valid_polygon_passes(self):
        ok, msg = validate_polygon(VALID_POLYGON)
        assert ok is True
        assert msg == ""

    def test_wrong_type_fails(self):
        bad = {"type": "Point", "coordinates": [36.94, -0.42]}
        ok, msg = validate_polygon(bad)
        assert ok is False
        assert "Polygon" in msg

    def test_not_closed_fails(self):
        bad = {
            "type": "Polygon",
            "coordinates": [[
                [36.94, -0.42],
                [36.95, -0.42],
                [36.95, -0.41],
                [36.94, -0.41],
                # Missing closing point
            ]]
        }
        ok, msg = validate_polygon(bad)
        assert ok is False

    def test_too_few_points_fails(self):
        bad = {
            "type": "Polygon",
            "coordinates": [[[36.94, -0.42], [36.95, -0.42], [36.94, -0.42]]]
        }
        ok, msg = validate_polygon(bad)
        assert ok is False

    def test_invalid_longitude_fails(self):
        bad = {
            "type": "Polygon",
            "coordinates": [[
                [200.0, -0.42],
                [36.95, -0.42],
                [36.95, -0.41],
                [36.94, -0.41],
                [200.0, -0.42],
            ]]
        }
        ok, msg = validate_polygon(bad)
        assert ok is False
        assert "longitude" in msg

    def test_non_dict_fails(self):
        ok, msg = validate_polygon("not a dict")
        assert ok is False

    def test_missing_coordinates_fails(self):
        ok, msg = validate_polygon({"type": "Polygon"})
        assert ok is False


class TestPolygonAreaAcres:

    def test_realistic_farm_area(self):
        """A ~300m × 280m polygon should be roughly 20 acres."""
        polygon = {
            "type": "Polygon",
            "coordinates": [[
                [36.9000, -0.4200],
                [36.9027, -0.4200],
                [36.9027, -0.4175],
                [36.9000, -0.4175],
                [36.9000, -0.4200],
            ]]
        }
        area = polygon_area_acres(polygon)
        assert area > 0
        assert 10 < area < 50    # rough sanity band

    def test_small_farm_area(self):
        """Tiny 1-acre polygon returns a small positive number."""
        area = polygon_area_acres(VALID_POLYGON)
        assert 0 < area < 10

    def test_invalid_polygon_returns_zero(self):
        area = polygon_area_acres({"type": "Polygon", "coordinates": [[]]})
        assert area == 0.0


class TestPolygonCentroid:

    def test_centroid_within_bounds(self):
        lng, lat = polygon_centroid(VALID_POLYGON)
        assert -180 <= lng <= 180
        assert -90  <= lat <= 90

    def test_centroid_near_polygon_centre(self):
        """Centroid of Nyeri polygon should be near -0.42, 36.94"""
        lng, lat = polygon_centroid(VALID_POLYGON)
        assert abs(lng - 36.9415) < 0.01
        assert abs(lat - (-0.4188)) < 0.01


class TestNDVIUtils:

    def test_valid_ndvi_values(self):
        assert is_valid_ndvi(0.0)   is True
        assert is_valid_ndvi(0.65)  is True
        assert is_valid_ndvi(1.0)   is True

    def test_invalid_ndvi_values(self):
        assert is_valid_ndvi(-0.1)  is False
        assert is_valid_ndvi(1.01)  is False
        assert is_valid_ndvi("bad") is False

    def test_clamp_ndvi(self):
        assert clamp_ndvi(1.5)  == 1.0
        assert clamp_ndvi(-0.2) == 0.0
        assert clamp_ndvi(0.65) == 0.65

    def test_health_labels(self):
        assert ndvi_health_label(0.80) == "excellent"
        assert ndvi_health_label(0.60) == "good"
        assert ndvi_health_label(0.45) == "moderate"
        assert ndvi_health_label(0.30) == "poor"
        assert ndvi_health_label(0.10) == "critical"

    def test_health_colours(self):
        assert ndvi_health_color(0.65) == "#1D9E75"   # green
        assert ndvi_health_color(0.50) == "#F39C12"   # amber
        assert ndvi_health_color(0.20) == "#E74C3C"   # red


class TestComputePayoutAmount:

    def test_severe_drought_payout(self):
        """NDVI deviation > 40% should give 80% of coverage."""
        payout = compute_payout_amount(
            coverage_amount_kes=10_000,
            stress_type="drought",
            confidence=0.91,
            ndvi_deviation_pct=-45.0,
        )
        assert payout >= 7_500    # ~80% of 10,000 + confidence bonus

    def test_moderate_stress_payout(self):
        """NDVI deviation 25–40% should give ~50% of coverage."""
        payout = compute_payout_amount(
            coverage_amount_kes=10_000,
            stress_type="drought",
            confidence=0.80,
            ndvi_deviation_pct=-30.0,
        )
        assert 4_000 < payout < 7_000

    def test_mild_stress_payout(self):
        payout = compute_payout_amount(
            coverage_amount_kes=10_000,
            stress_type="flood",
            confidence=0.75,
            ndvi_deviation_pct=-18.0,
        )
        assert payout > 0
        assert payout < 5_000

    def test_payout_rounded_to_50(self):
        payout = compute_payout_amount(10_000, "drought", 0.85, -35.0)
        assert payout % 50 == 0

    def test_minimum_payout_floor(self):
        payout = compute_payout_amount(100, "drought", 0.73, -16.0)
        assert payout >= 50


class TestBuildFeatureVector:

    def test_all_keys_present(self):
        fv = build_feature_vector(
            ndvi_zscore=-1.8,
            ndvi_roc=-0.04,
            rainfall_anomaly_mm=-25.0,
        )
        expected_keys = {
            "ndvi_zscore", "ndvi_roc", "rainfall_anomaly_mm",
            "day_of_year", "seasonal_factor", "cloud_contaminated",
        }
        assert set(fv.keys()) == expected_keys

    def test_seasonal_factor_is_float(self):
        fv = build_feature_vector(-1.0, 0.0, 0.0)
        assert isinstance(fv["seasonal_factor"], float)

    def test_cloud_contaminated_is_int(self):
        fv = build_feature_vector(-1.0, 0.0, 0.0, cloud_contaminated=True)
        assert fv["cloud_contaminated"] == 1

    def test_specific_date_features(self):
        dt = date(2026, 4, 20)
        fv = build_feature_vector(-1.0, 0.0, 0.0, dt=dt)
        assert fv["day_of_year"] == 110     # April 20 = day 110
        assert isinstance(fv["seasonal_factor"], float)


class TestDateHelpers:

    def test_week_of_year_range(self):
        w = week_of_year()
        assert 1 <= w <= 53

    def test_day_of_year_range(self):
        d = day_of_year()
        assert 1 <= d <= 366

    def test_month_names_en(self):
        assert month_name_en(1)  == "January"
        assert month_name_en(4)  == "April"
        assert month_name_en(12) == "December"

    def test_month_names_sw(self):
        assert month_name_sw(1)  == "Januari"
        assert month_name_sw(4)  == "Aprili"
        assert month_name_sw(12) == "Desemba"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — sentinel.py tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMockNDVI:

    def test_mock_ndvi_returns_required_keys(self):
        result = _mock_ndvi(VALID_POLYGON, "2024-06-01")
        required = {"ndvi_mean", "ndvi_std", "cloud_cover_pct",
                    "valid_pixels_pct", "date", "cloud_contaminated"}
        assert required.issubset(result.keys())

    def test_mock_ndvi_values_in_range(self):
        result = _mock_ndvi(VALID_POLYGON, "2024-06-01")
        assert 0.0 <= result["ndvi_mean"] <= 1.0
        assert result["ndvi_std"] >= 0.0
        assert 0.0 <= result["cloud_cover_pct"] <= 100.0
        assert isinstance(result["cloud_contaminated"], bool)

    def test_mock_ndvi_is_deterministic(self):
        """Same polygon + date must always return the same value."""
        r1 = _mock_ndvi(VALID_POLYGON, "2024-06-01")
        r2 = _mock_ndvi(VALID_POLYGON, "2024-06-01")
        assert r1["ndvi_mean"] == r2["ndvi_mean"]

    def test_mock_ndvi_differs_by_date(self):
        r1 = _mock_ndvi(VALID_POLYGON, "2024-01-01")
        r2 = _mock_ndvi(VALID_POLYGON, "2024-07-01")
        # Seasonal variation should produce different values
        assert r1["ndvi_mean"] != r2["ndvi_mean"]

    def test_mock_historical_ndvi_structure(self):
        records = _mock_historical_ndvi(years=2)
        assert len(records) == 104    # 52 weeks × 2 years
        assert "week_of_year" in records[0]
        assert "mean_ndvi"    in records[0]

    def test_mock_historical_ndvi_values_valid(self):
        records = _mock_historical_ndvi(years=1)
        for r in records:
            assert 0.0 < r["mean_ndvi"] < 1.0
            assert 1 <= r["week_of_year"] <= 52


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — baseline.py tests
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildFarmBaseline:

    def test_baseline_has_52_weeks(self):
        """Every week 1–52 must be present after build."""
        baseline = build_farm_baseline(VALID_POLYGON, years=2)
        assert len(baseline) == 52
        for week in range(1, 53):
            assert str(week) in baseline

    def test_baseline_values_in_ndvi_range(self):
        baseline = build_farm_baseline(VALID_POLYGON, years=2)
        for week_data in baseline.values():
            assert 0.0 < week_data["mean"] < 1.0
            assert week_data["std"] >= 0.025

    def test_baseline_has_required_keys(self):
        baseline = build_farm_baseline(VALID_POLYGON, years=1)
        for week_data in baseline.values():
            assert "mean"         in week_data
            assert "std"          in week_data
            assert "sample_count" in week_data


class TestComputeNDVIZscore:

    @pytest.fixture
    def sample_baseline(self):
        return {
            "20": {"mean": 0.62, "std": 0.05, "sample_count": 4},
            "21": {"mean": 0.65, "std": 0.06, "sample_count": 4},
        }

    def test_below_baseline_is_negative(self, sample_baseline):
        z = compute_ndvi_zscore(0.40, week_of_year=20, baseline=sample_baseline)
        assert z < 0

    def test_above_baseline_is_positive(self, sample_baseline):
        z = compute_ndvi_zscore(0.75, week_of_year=20, baseline=sample_baseline)
        assert z > 0

    def test_at_baseline_is_near_zero(self, sample_baseline):
        z = compute_ndvi_zscore(0.62, week_of_year=20, baseline=sample_baseline)
        assert abs(z) < 0.1

    def test_severe_drop_returns_large_negative(self, sample_baseline):
        z = compute_ndvi_zscore(0.20, week_of_year=20, baseline=sample_baseline)
        assert z < -3.0

    def test_missing_week_returns_zero(self, sample_baseline):
        z = compute_ndvi_zscore(0.50, week_of_year=99, baseline=sample_baseline)
        assert z == 0.0


class TestComputeNDVIDeviation:

    def test_deviation_negative_when_below(self):
        baseline = {"20": {"mean": 0.62, "std": 0.05, "sample_count": 4}}
        dev = compute_ndvi_deviation_pct(0.42, week_of_year=20, baseline=baseline)
        assert dev < 0
        assert abs(dev - (-32.26)) < 1.0    # ~32% below

    def test_deviation_positive_when_above(self):
        baseline = {"20": {"mean": 0.62, "std": 0.05, "sample_count": 4}}
        dev = compute_ndvi_deviation_pct(0.75, week_of_year=20, baseline=baseline)
        assert dev > 0


class TestComputeRateOfChange:

    def test_declining_ndvi_gives_negative_roc(self):
        history = [0.65, 0.58, 0.50, 0.42]
        roc = compute_rate_of_change(history)
        assert roc < 0

    def test_rising_ndvi_gives_positive_roc(self):
        history = [0.40, 0.48, 0.57, 0.65]
        roc = compute_rate_of_change(history)
        assert roc > 0

    def test_stable_ndvi_near_zero(self):
        history = [0.60, 0.61, 0.60, 0.61]
        roc = compute_rate_of_change(history)
        assert abs(roc) < 0.02

    def test_single_value_returns_zero(self):
        assert compute_rate_of_change([0.60]) == 0.0

    def test_empty_list_returns_zero(self):
        assert compute_rate_of_change([]) == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — model.py inference tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPredictStress:

    def test_response_has_required_keys(self):
        result = predict_stress(
            ndvi_zscore=-2.5,
            ndvi_roc=-0.06,
            rainfall_anomaly_mm=-30.0,
            day_of_year=140,
        )
        required = {
            "stress_type", "confidence", "payout_recommended",
            "class_probabilities", "explanation_en", "explanation_sw",
            "cloud_contaminated",
        }
        assert required.issubset(result.keys())

    def test_drought_scenario_predicts_drought(self):
        """Severe NDVI drop + large rainfall deficit → drought."""
        result = predict_stress(
            ndvi_zscore=-2.8,
            ndvi_roc=-0.07,
            rainfall_anomaly_mm=-40.0,
            day_of_year=130,
        )
        assert result["stress_type"] == "drought"
        assert result["payout_recommended"] is True

    def test_healthy_scenario_predicts_no_stress(self):
        """NDVI above baseline + normal rainfall → no stress."""
        result = predict_stress(
            ndvi_zscore=0.5,
            ndvi_roc=0.02,
            rainfall_anomaly_mm=3.0,
            day_of_year=120,
        )
        assert result["stress_type"] == "no_stress"
        assert result["payout_recommended"] is False

    def test_cloud_contaminated_suppresses_payout(self):
        """Even strong stress signals should not trigger payout if cloud-contaminated."""
        result = predict_stress(
            ndvi_zscore=-2.5,
            ndvi_roc=-0.06,
            rainfall_anomaly_mm=-30.0,
            day_of_year=140,
            cloud_contaminated=True,
        )
        assert result["payout_recommended"] is False
        assert result["cloud_contaminated"]  is True

    def test_confidence_is_between_0_and_1(self):
        result = predict_stress(
            ndvi_zscore=-1.0,
            ndvi_roc=-0.02,
            rainfall_anomaly_mm=-10.0,
            day_of_year=100,
        )
        assert 0.0 <= result["confidence"] <= 1.0

    def test_class_probabilities_sum_to_one(self):
        result = predict_stress(
            ndvi_zscore=-2.0,
            ndvi_roc=-0.05,
            rainfall_anomaly_mm=-25.0,
            day_of_year=150,
        )
        total = sum(result["class_probabilities"].values())
        assert abs(total - 1.0) < 0.01

    def test_explanation_text_not_empty(self):
        result = predict_stress(
            ndvi_zscore=-2.5,
            ndvi_roc=-0.06,
            rainfall_anomaly_mm=-30.0,
            day_of_year=140,
        )
        assert len(result["explanation_en"]) > 10
        assert len(result["explanation_sw"]) > 10

    def test_flood_scenario(self):
        """NDVI drop + large rainfall surplus → flood."""
        result = predict_stress(
            ndvi_zscore=-1.6,
            ndvi_roc=-0.04,
            rainfall_anomaly_mm=+45.0,
            day_of_year=110,
        )
        # Model should lean toward flood
        probs = result["class_probabilities"]
        assert probs.get("flood", 0) > probs.get("drought", 0)

    def test_stress_type_is_valid_class(self):
        result = predict_stress(0.1, 0.0, 0.0, 100)
        assert result["stress_type"] in {
            "no_stress", "drought", "flood", "pest_disease"
        }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — FastAPI endpoint integration tests
# ══════════════════════════════════════════════════════════════════════════════

class TestFastAPIEndpoints:
    """
    Integration tests using FastAPI TestClient.
    These run against the actual app with mock satellite data.
    """

    @pytest.fixture(scope="class")
    def client(self):
        from fastapi.testclient import TestClient
        # Import from app directory
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.main import app
        return TestClient(app)

    def test_health_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "CropSure" in resp.json().get("service", "")

    def test_build_baseline_endpoint(self, client):
        payload = {
            "farm_id":         "test-farm-001",
            "polygon_geojson": VALID_POLYGON,
            "years":           2,
        }
        resp = client.post("/build-baseline", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["farm_id"] == "test-farm-001"
        assert "baseline" in data
        assert data["weeks_covered"] == 52

    def test_analyze_endpoint_returns_required_fields(self, client):
        payload = {
            "farm_id":             "test-farm-002",
            "polygon_geojson":     VALID_POLYGON,
            "baseline_dict":       None,
            "recent_ndvi_history": [0.62, 0.55, 0.48],
            "expected_payout_kes": 4800.0,
        }
        resp = client.post("/analyze", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        required = {
            "farm_id", "analysis_date", "ndvi_current", "ndvi_baseline_mean",
            "ndvi_deviation_pct", "ndvi_zscore", "stress_type",
            "confidence", "payout_recommended", "explanation_en", "explanation_sw",
        }
        assert required.issubset(data.keys())

    def test_simulate_drought_endpoint(self, client):
        payload = {
            "farm_id":             "test-farm-003",
            "polygon_geojson":     VALID_POLYGON,
            "expected_payout_kes": 5000.0,
        }
        resp = client.post("/analyze/simulate-drought", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["stress_type"]        == "drought"
        assert data["payout_recommended"] is True
        assert data["confidence"]         >= 0.90
        assert data.get("demo_mode")      is True

    def test_analyze_with_invalid_polygon_returns_error(self, client):
        payload = {
            "farm_id":         "bad-farm",
            "polygon_geojson": {"type": "Point", "coordinates": [36.94, -0.42]},
        }
        resp = client.post("/analyze", json=payload)
        # Should return 422 (validation error) or 400
        assert resp.status_code in {400, 422, 502}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Edge cases and boundary conditions
# ══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_ndvi_zscore_at_exact_threshold(self):
        """z = -1.5 is the drought detection boundary."""
        baseline = {"20": {"mean": 0.60, "std": 0.04, "sample_count": 5}}
        ndvi_at_threshold = 0.60 - (1.5 * 0.04)   # exactly -1.5 z
        z = compute_ndvi_zscore(ndvi_at_threshold, 20, baseline)
        assert abs(z - (-1.5)) < 0.01

    def test_payout_never_exceeds_coverage(self):
        """Payout amount must never exceed coverage amount."""
        payout = compute_payout_amount(
            coverage_amount_kes=5_000,
            stress_type="drought",
            confidence=1.0,
            ndvi_deviation_pct=-99.0,
        )
        assert payout <= 5_000

    def test_model_handles_extreme_zscore(self):
        """Model must not crash on extreme z-score values."""
        result = predict_stress(
            ndvi_zscore=-10.0,
            ndvi_roc=-0.2,
            rainfall_anomaly_mm=-100.0,
            day_of_year=1,
        )
        assert result["stress_type"] in {"no_stress", "drought", "flood", "pest_disease"}

    def test_model_handles_positive_anomaly(self):
        """Positive rainfall with negative NDVI → flood, not drought."""
        result = predict_stress(
            ndvi_zscore=-2.0,
            ndvi_roc=-0.05,
            rainfall_anomaly_mm=+60.0,
            day_of_year=100,
        )
        probs = result["class_probabilities"]
        assert probs.get("flood", 0) >= probs.get("drought", 0)

    def test_area_calculation_is_symmetric(self):
        """Reversing polygon winding order should give same area."""
        polygon_fwd = {
            "type": "Polygon",
            "coordinates": [[
                [36.94, -0.42], [36.96, -0.42],
                [36.96, -0.40], [36.94, -0.40], [36.94, -0.42]
            ]]
        }
        polygon_rev = {
            "type": "Polygon",
            "coordinates": [[
                [36.94, -0.42], [36.94, -0.40],
                [36.96, -0.40], [36.96, -0.42], [36.94, -0.42]
            ]]
        }
        assert abs(polygon_area_acres(polygon_fwd) - polygon_area_acres(polygon_rev)) < 0.1

    def test_baseline_with_one_year_still_returns_52_weeks(self):
        baseline = build_farm_baseline(VALID_POLYGON, years=1)
        assert len(baseline) == 52


# ── Run configuration ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
