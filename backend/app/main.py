from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.config import ROOT_DIR, get_settings
from app.db.engine import GeoDB, init_geodb
from app.db.seed import seed_geodb
from app.geospatial.features import init_extractor
from app.geospatial.hexgrid import hotspot_grid
from app.geospatial.loader import get_store
from app.geospatial.routing import router as road_router
from app.rag.store import rag_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print("═" * 56)
    print("  GeoReady-AI backend starting")
    print("═" * 56)
    store = get_store(settings.data_dir)
    db: GeoDB | None = None
    try:
        db = init_geodb(settings.database_url, settings.duckdb_path)
    except Exception as exc:  # noqa: BLE001
        print(f"spatial DB unavailable ({exc}) — memory-mode feature extraction")
        db = None

    db_spatial_ok = db is None or db.mode == "postgis" or getattr(db, "spatial_loaded", True)
    if db is not None and not db_spatial_ok:
        print("⚠ duckdb 'spatial' unavailable — degraded to in-memory feature mode\n"
              "  (vendored copy used where possible)")
        try:
            db.create_rag_table()
        except Exception as exc2:
            print(f"degraded rag table init: {exc2}")
    feature_db = db if db_spatial_ok else None

    try:
        if feature_db is not None and feature_db.table_empty("population_cells"):
            seed_geodb(feature_db, store)
    except Exception as exc:  # noqa: BLE001
        print(f"seed failed ({exc}) — continuing with in-memory features")
        feature_db = None

    extractor = init_extractor(feature_db, store)
    hotspot_grid.build(store, extractor, feature_db)
    road_router.build(store)
    rag_store.warmup()
    yield


app = FastAPI(
    title="GeoReady-AI",
    version="1.0.0",
    description="AI-Powered GeoSpatial Site Readiness Analyzer — Rajkot",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

DIST = ROOT_DIR / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
