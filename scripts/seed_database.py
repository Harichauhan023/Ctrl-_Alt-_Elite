#!/usr/bin/env python3
"""Seed the spatial database (PostGIS hero or DuckDB fallback).

Usage:
    python scripts/seed_database.py              # auto mode (Postgres if DATABASE_URL set)
    python scripts/seed_database.py --duckdb     # force embedded DuckDB
    python scripts/seed_database.py --keep       # do not drop existing tables
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings            # noqa: E402
from app.db.engine import init_geodb           # noqa: E402
from app.db.seed import seed_geodb             # noqa: E402
from app.geospatial.loader import get_store    # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--duckdb", action="store_true", help="force embedded DuckDB")
    ap.add_argument("--keep", action="store_true", help="keep existing tables")
    args = ap.parse_args()

    s = get_settings()
    dsn = "" if args.duckdb else s.database_url
    db = init_geodb(dsn, s.duckdb_path)
    store = get_store(s.data_dir)
    counts = seed_geodb(db, store, drop=not args.keep)
    print("✔ Done:", db.info()["tables"])
    if not counts:
        raise SystemExit("nothing seeded — check data/ directory")


if __name__ == "__main__":
    main()
