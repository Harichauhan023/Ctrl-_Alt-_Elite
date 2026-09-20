from __future__ import annotations

import json
import sys
from pathlib import Path

from app.config import ROOT_DIR, get_settings

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ml.feature_schema import FEATURES, named_vector_from_features, vector_from_features  # noqa: E402


class MLService:
    def __init__(self):
        s = get_settings()
        models = Path(s.ml_dir) / "models"
        self.model = None
        self.metrics: dict = {}
        self.feature_importance: list[dict] = []
        self.error: str | None = None
        try:
            import joblib
            self.model = joblib.load(models / "site_readiness_model.joblib")
            self.metrics = json.loads((models / "metrics.json").read_text())
            raw_fi = json.loads((models / "feature_importance.json").read_text())
            # normalise key — artifacts emit {"feature", "importance"};
            # the public API contract is {"name", "importance"}
            self.feature_importance = [
                {"name": d.get("name") or d.get("feature"), "importance": d["importance"]}
                for d in raw_fi
            ]
            print(f"✔ ML model loaded — R² {self.metrics.get('r2')}, "
                  f"MAE {self.metrics.get('mae')} ({models})")
        except Exception as exc:  # noqa: BLE001
            self.error = str(exc)
            print(f"ML model unavailable ({exc}) — analysis continues without ML prediction")

    @property
    def available(self) -> bool:
        return self.model is not None

    def predict(self, fe: dict) -> float:
        vec = vector_from_features(fe)
        p = float(self.model.predict([vec])[0])
        return round(min(100.0, max(0.0, p)), 1)

    def feature_vector(self, fe: dict) -> dict:
        return named_vector_from_features(fe)

    def meta(self) -> dict:
        return {
            "available": self.available,
            "error": self.error,
            "model": self.metrics.get("model"),
            "features": FEATURES,
            "n_samples": self.metrics.get("n_samples"),
            "mae": self.metrics.get("mae"),
            "rmse": self.metrics.get("rmse"),
            "r2": self.metrics.get("r2"),
            "trained_at": self.metrics.get("trained_at"),
            "label_method": self.metrics.get("label_method"),
            "feature_importance": self.feature_importance,
        }


_ML: MLService | None = None


def get_ml_service() -> MLService:
    global _ML
    if _ML is None:
        _ML = MLService()
    return _ML
