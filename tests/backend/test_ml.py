import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

import sys
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from ml.feature_schema import FEATURES, NEUTRAL_LANDUSE, vector_from_features  # noqa: E402


def test_model_artifact_loads():
    from app.services.ml_service import MLService
    svc = MLService()
    assert svc.available, f"artifact missing: {svc.error}"


def test_feature_schema_is_13():
    assert len(FEATURES) == 13
    saved = json.loads((ROOT / "ml" / "models" / "metrics.json").read_text())
    assert saved["features"] == FEATURES          # served model == training schema


def test_neutral_landuse_matches_business_configs():
    """The neutral table must be the MEAN of the six per-business tables."""
    from app.scoring.config import BUSINESS_CONFIGS
    cats = set()
    for cfg in BUSINESS_CONFIGS.values():
        cats |= set(cfg["landuse"])
    for cat in cats:
        mean = sum(cfg["landuse"].get(cat, 50) for cfg in BUSINESS_CONFIGS.values()) / len(BUSINESS_CONFIGS)
        assert abs(NEUTRAL_LANDUSE[cat] - mean) < 0.1, cat


def test_prediction_is_numeric_and_bounded(extractor, store):
    from app.services.ml_service import get_ml_service
    svc = get_ml_service()
    x, y = store.project_point(22.3039, 70.8022)
    fe = extractor.extract(x, y)
    p = svc.predict(fe)
    assert isinstance(p, float)
    assert 0.0 <= p <= 100.0


def test_metrics_file_is_real_and_sane():
    m = json.loads((ROOT / "ml" / "models" / "metrics.json").read_text())
    assert m["n_samples"] == 10000
    assert 0 < m["mae"] < 15
    assert 0.5 < m["r2"] <= 1.0
    fi = json.loads((ROOT / "ml" / "models" / "feature_importance.json").read_text())
    assert len(fi) == 13
    assert abs(sum(d["importance"] for d in fi) - 1.0) < 0.01


def test_feature_vector_shape(extractor, store):
    x, y = store.project_point(22.29, 70.77)
    vec = vector_from_features(extractor.extract(x, y))
    assert len(vec) == 13 and all(isinstance(v, float) for v in vec)
