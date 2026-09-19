"""
GeoReady-AI — FastAPI application entrypoint.

Startup: load geospatial layers → build H3 hotspot grid → warm RAG embeddings
(background thread). Serves the built frontend from /frontend/dist when present.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api import api_router
from .config import ROOT_DIR, get_settings
from .db.engine import GeoDB, init_geodb
from .db.seed import seed_geodb
from .geospatial.features import init_extractor
from .geospatial.hexgrid import hotspot_grid
from .geospatial.loader import get_store
from .geospatial.routing import router as road_router
from .rag.store import rag_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    print("═" * 56)
    print("  GeoReady-AI backend starting")
    print("═" * 56)
    store = get_store(settings.data_dir)                 # 1. load all layers
    db: GeoDB | None = None
    try:
        db = init_geodb(settings.database_url, settings.duckdb_path)   # 2. spatial DB
        if db.table_empty("population_cells"):
            seed_geodb(db, store)                        # 2b. auto-seed once
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ spatial DB unavailable ({exc}) — memory-mode feature extraction")
        db = None
    extractor = init_extractor(db, store)                # 3. SQL feature extractor
    hotspot_grid.build(store, extractor, db)             # 4. H3 grid (→ materialise to DB)
    road_router.build(store)                             # 5. routing graph
    rag_store.warmup()                                   # 6. RAG: ingest + vector warm (foreground, ~2-4s)
    yield


app = FastAPI(
    title="GeoReady-AI",
    version="1.0.0",
    description="AI-Powered GeoSpatial Site Readiness Analyzer — Rajkot (Bit N Build '26, PS-2)",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

# Serve the production frontend build when it exists (single-origin demo mode).
DIST = ROOT_DIR / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
