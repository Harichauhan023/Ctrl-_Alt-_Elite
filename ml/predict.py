#!/usr/bin/env python3
"""Live prediction CLI (spec §22: features → model inference).

    python ml/predict.py 22.3039 70.8022

Extracts REAL features for the coordinate through the backend pipeline and
runs the saved model — the same path /api/analyze takes.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.config import get_settings                  # noqa: E402
from app.db.engine import init_geodb                 # noqa: E402
from app.db.seed import seed_geodb                   # noqa: E402
from app.geospatial.features import init_extractor   # noqa: E402
from app.geospatial.loader import get_store          # noqa: E402
from app.services.ml_service import get_ml_service   # noqa: E402


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: python ml/predict.py LAT LNG")
    lat, lng = float(sys.argv[1]), float(sys.argv[2])
    s = get_settings()
    store = get_store(s.data_dir)
    db = init_geodb(s.database_url, s.duckdb_path)
    if db.table_empty("population_cells"):
        seed_geodb(db, store)
    extractor = init_extractor(db, store)
    ml = get_ml_service()
    if not ml.available:
        raise SystemExit("model artifact missing — run python ml/train.py first")
    x, y = store.project_point(lat, lng)
    fe = extractor.extract(x, y)
    p = ml.predict(fe)
    vec = ml.feature_vector(fe)
    print(f"\nML Predicted Readiness @ ({lat}, {lng}):  {p}/100")
    for k, v in vec.items():
        print(f"  {k:<28} {v}")


if __name__ == "__main__":
    main()
