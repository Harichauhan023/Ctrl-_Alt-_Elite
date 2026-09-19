#!/usr/bin/env python3
"""Re-evaluate the saved model against the training data (spec §11).

    python ml/evaluate.py

Loads the persisted artifact (never a rebuilt one) and reports the same
metrics.json should contain — proof the saved model is what's served.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.feature_schema import FEATURES                     # noqa: E402

MODELS = ROOT / "ml" / "models"


def main() -> None:
    model = joblib.load(MODELS / "site_readiness_model.joblib")
    df = pd.read_csv(ROOT / "ml" / "training_data.csv")
    X = df[FEATURES].to_numpy(dtype=float)
    y = df["target_readiness"].to_numpy(dtype=float)
    pred = model.predict(X)
    mae = float(mean_absolute_error(y, pred))
    rmse = float(np.sqrt(mean_squared_error(y, pred)))
    r2 = float(r2_score(y, pred))
    print(f"saved model on full data  n={len(X):,}")
    print(f"  MAE  = {mae:.2f}")
    print(f"  RMSE = {rmse:.2f}")
    print(f"  R²   = {r2:.3f}")
    print(f"  prediction range = [{pred.min():.1f}, {pred.max():.1f}]")
    stored = json.loads((MODELS / "metrics.json").read_text())
    print(f"  (train-time holdout: MAE {stored['mae']}, RMSE {stored['rmse']}, R² {stored['r2']})")


if __name__ == "__main__":
    main()
