"""Meta endpoints: health, layer catalogue, business types, dashboard stats."""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException

from ..ai.provider import provider_manager
from ..db.engine import get_geodb
from ..geospatial.features import get_extractor
from ..geospatial.hexgrid import hotspot_grid
from ..geospatial.loader import ALL_LAYERS, get_store
from ..geospatial.routing import router as road_router
from ..rag.store import rag_store
from ..scoring.config import BUSINESS_CONFIGS
from ..services.ml_service import get_ml_service

router = APIRouter()
_STARTED = time.time()


@router.get("/health")
def health():
    store = get_store()
    db = get_geodb()
    try:
        extractor = get_extractor()
        feature_mode = extractor.mode
    except Exception:
        feature_mode = "unavailable"
    ml_meta = get_ml_service().meta()
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _STARTED),
        "layers_loaded": {k: len(v) for k, v in store.layers.items()},
        "hotspot_cells": len(hotspot_grid.cells),
        "database": db.info() if db else {"mode": "memory-fallback"},
        "feature_mode": feature_mode,          # postgis | duckdb | memory
        "routing": {"engine": "networkx", "ready": road_router.ready,
                    "edges": road_router.edges},
        "ml": {"available": ml_meta["available"], "r2": ml_meta.get("r2"),
               "mae": ml_meta.get("mae"), "n_samples": ml_meta.get("n_samples")},
        "ai": {
            "providers_configured": provider_manager.configured,
            "providers": provider_manager.status(),
            "rag_mode": rag_store.mode,
            "llm_calls": provider_manager.call_count,
            "fallbacks": provider_manager.fallback_count,
        },
        "version": "1.0.0",
    }


@router.get("/layers")
def layer_catalog():
    store = get_store()
    return {"study_area": store.meta.get("area", "Rajkot"), "center": store.meta.get("center"),
            "bbox": store.bbox, "layers": store.layer_catalog(),
            "notes": store.meta.get("notes", "")}


@router.get("/layers/{name}/data")
def layer_data(name: str):
    if name not in ALL_LAYERS:
        raise HTTPException(404, f"Unknown layer '{name}'. Available: {', '.join(ALL_LAYERS)}")
    store = get_store()
    gdf = store.layers.get(name)
    if gdf is None:
        raise HTTPException(404, f"Layer '{name}' has no data (fetch may have failed).")
    return json.loads(gdf.to_json())


@router.get("/business-types")
def business_types():
    return {"business_types": [
        {"key": k, "label": v["label"], "description": v["description"],
         "default_weights": v["weights"], "competition_polarity": v["competition_polarity"]}
        for k, v in BUSINESS_CONFIGS.items()
    ]}


@router.get("/rag/search")
def rag_search(q: str, k: int = 6):
    """Knowledge-explorer endpoint — raw semantic retrieval, exposed for the UI.
    Returns retrieved chunks WITH source paths + similarity scores (spec §20)."""
    chunks = rag_store.retrieve(q, k=min(k, 12))
    return {"query": q, "mode": rag_store.mode,
            "total_docs": rag_store.total_docs(),
            "chunks": [{"title": c["title"], "text": c["text"], "tags": c.get("tags", []),
                        "source": c.get("source", ""), "score": c["score"]} for c in chunks]}


@router.get("/stats")
def stats():
    store = get_store()
    dist = hotspot_grid.distribution("EV_CHARGING", None) if hotspot_grid.ready else {}
    return {
        "study_area": store.meta.get("area", "Rajkot Metropolitan Area"),
        "total_modelled_population": int(store.pop_vals.sum()) if store.pop_vals is not None else 0,
        "road_network_km": round(store.total_road_km, 1),
        "competitors": int(len(store.comp_xy)) if store.comp_xy is not None else 0,
        "sites": len(store.sites),
        "hotspot_cells": len(hotspot_grid.cells),
        "ev_readiness_distribution": dist,
        "land_use_zones": len(store.landuse_polys),
        "risk_zones": len(store.risk_polys),
    }
