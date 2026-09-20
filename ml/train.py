from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.feature_schema import FEATURES                     # noqa: E402

DATA = ROOT / "ml" / "training_data.csv"
MODELS = ROOT / "ml" / "models"

PARAMS = dict(n_estimators=100, max_depth=10, min_samples_leaf=2,
              n_jobs=-1, random_state=42)


def main() -> None:
    if not DATA.exists():
        raise SystemExit("training_data.csv missing — run scripts/generate_training_data.py first")
    df = pd.read_csv(DATA)
    missing = [f for f in FEATURES if f not in df.columns]
    if missing:
        raise SystemExit(f"feature schema mismatch — missing columns: {missing}")
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["target_readiness"].to_numpy(dtype=float)
    print(f"▶ Training on {len(X):,} candidates × {X.shape[1]} features")

    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    t0 = time.time()
    model = RandomForestRegressor(**PARAMS)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    mae = float(mean_absolute_error(yte, pred))
    rmse = float(np.sqrt(mean_squared_error(yte, pred)))
    r2 = float(r2_score(yte, pred))
    print(f"✔ trained in {time.time() - t0:.1f}s")
    print(f"  holdout MAE  = {mae:.2f}")
    print(f"  holdout RMSE = {rmse:.2f}")
    print(f"  holdout R²   = {r2:.3f}")

    MODELS.mkdir(parents=True, exist_ok=True)
    model_path = MODELS / "site_readiness_model.joblib"
    joblib.dump(model, model_path, compress=9)
    size_mb = model_path.stat().st_size / 1e6

    metrics = {
        "model": "RandomForestRegressor",
        "params": PARAMS,
        "sklearn_version": sklearn.__version__,
        "n_samples": int(len(X)),
        "n_train": int(len(Xtr)),
        "n_test": int(len(Xte)),
        "n_features": len(FEATURES),
        "features": FEATURES,
        "mae": round(mae, 3), "rmse": round(rmse, 3), "r2": round(r2, 4),
        "target": "target_readiness (0–100, documented rubric + N(0,2.2) noise)",
        "label_method": "ml/labels.py",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_size_mb": round(size_mb, 1),
    }
    (MODELS / "metrics.json").write_text(json.dumps(metrics, indent=2))

    importances = sorted(
        ({"feature": f, "name": f, "importance": round(float(v), 4)}
         for f, v in zip(FEATURES, model.feature_importances_)),
        key=lambda d: -d["importance"])
    (MODELS / "feature_importance.json").write_text(json.dumps(importances, indent=2))
    print(f"✔ artifacts saved ({size_mb:.1f} MB model) → {MODELS}/")
    print("  top features:", ", ".join(f"{d['feature']} {d['importance']:.2f}"
                                    for d in importances[:5]))


if __name__ == "__main__":
    main()
