#!/usr/bin/env python3
"""Generate the ML training dataset (spec §9).

    n candidate locations → REAL feature extraction (same SQL pipeline)
    → documented label rubric (ml/labels.py) → ml/training_data.csv

Usage:
    python scripts/generate_training_data.py            # 10,000 rows (default)
    python scripts/generate_training_data.py -n 2000    # quick pass
"""
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.config import get_settings                       # noqa: E402
from app.db.engine import init_geodb                      # noqa: E402
from app.db.seed import seed_geodb                        # noqa: E402
from app.geospatial.features import init_extractor        # noqa: E402
from app.geospatial.loader import get_store               # noqa: E402
from ml.feature_schema import FEATURES, vector_from_features  # noqa: E402
from ml.labels import label as label_for                  # noqa: E402


def sample_points(n: int, bbox: dict, rng: np.random.Generator) -> list[tuple[float, float]]:
    """75% uniform over the study bbox, 25% clustered near the urban core —
    keeps rural and urban candidates both represented."""
    lats = rng.uniform(bbox["s"], bbox["n"], n)
    lngs = rng.uniform(bbox["w"], bbox["e"], n)
    k = n // 4
    core_lat, core_lng = 22.3039, 70.8022
    lats[:k] = np.clip(rng.normal(core_lat, 0.045, k), bbox["s"], bbox["n"])
    lngs[:k] = np.clip(rng.normal(core_lng, 0.055, k), bbox["w"], bbox["e"])
    p = rng.permutation(n)
    return list(zip(lats[p].tolist(), lngs[p].tolist()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--n", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    s = get_settings()
    t0 = time.time()
    store = get_store(s.data_dir)
    db = init_geodb(s.database_url, s.duckdb_path)
    if db.table_empty("population_cells"):
        seed_geodb(db, store)
    extractor = init_extractor(db, store)
    print(f"extractor mode = {extractor.mode}")

    rng = np.random.default_rng(args.seed)
    pts = sample_points(args.n, store.bbox, rng)
    t0 = time.time()

    rows_out = []
    CHUNK = 500
    for lo in range(0, args.n, CHUNK):
        chunk = pts[lo:lo + CHUNK]
        utm = [store.project_point(lat, lng) for lat, lng in chunk]
        feats = extractor.extract_batch(utm)
        for (lat, lng), fe in zip(chunk, feats):
            vec = vector_from_features(fe)
            y = label_for(fe, store.pop_ref, rng)
            rows_out.append({
                "latitude": round(lat, 6), "longitude": round(lng, 6),
                **{name: round(v, 3) for name, v in zip(FEATURES, vec)},
                "target_readiness": round(y, 2),
            })
        done = min(lo + CHUNK, args.n)
        rate = done / (time.time() - t0)
        print(f"  … {done}/{args.n} candidates ({rate:.0f}/s)", flush=True)

    out = ROOT / "ml" / "training_data.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["latitude", "longitude", *FEATURES, "target_readiness"])
        w.writeheader()
        w.writerows(rows_out)
    n = len(rows_out)
    tgt = [r["target_readiness"] for r in rows_out]
    print(f"✔ Wrote {n:,} rows → {out}  ({time.time() - t0:.1f}s)")
    print(f"  target stats: mean={np.mean(tgt):.1f}  sd={np.std(tgt):.1f}  "
          f"min={min(tgt):.1f}  max={max(tgt):.1f}")


if __name__ == "__main__":
    main()
