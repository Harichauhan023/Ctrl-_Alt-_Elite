"""Catchment / accessibility analysis (PS-2 §35).

Primary: real routing engine — networkx single-source Dijkstra over the OSM
road graph (speed by road class) → true 10/20/30-min isochrones; population
inside each polygon via SQL (ST_Within). Fallback: labelled straight-line
travel shed at 18 km/h (never bricks).
"""
from __future__ import annotations

import numpy as np
from fastapi import APIRouter

from ..db.engine import get_geodb
from ..geospatial.features import get_extractor
from ..geospatial.loader import get_store
from ..geospatial.routing import MINUTES, router as road_router
from ..schemas.models import CatchmentRequest

router = APIRouter()

URBAN_SPEED_KMH = 18.0


@router.post("/catchment")
def catchment(req: CatchmentRequest):
    store = get_store()
    db = get_geodb()
    try:
        extractor = get_extractor()
    except Exception:
        extractor = None

    # ── real network isochrones ───────────────────────────────────────────
    if road_router.ready:
        try:
            rings = road_router.isochrones(store, req.latitude, req.longitude, extractor, db)
            return {
                "latitude": req.latitude, "longitude": req.longitude,
                "catchments": [{k: v for k, v in r.items() if k != "geometry"} for r in rings],
                "rings_geojson": {"type": "FeatureCollection", "features": [
                    {"type": "Feature",
                     "properties": {"minutes": r["minutes"],
                                    "nodes_reached": r["nodes_reached"]},
                     "geometry": r["geometry"]}
                    for r in rings]},
                "method": (f"road-network Dijkstra isochrones (OSM graph: "
                           f"{road_router.edges:,} edges, speed by road class)"),
                "engine": "networkx",
            }
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ network catchment failed ({exc}) — falling back to travel shed")

    # ── fallback: straight-line travel shed (labelled approximation) ─────
    x, y = store.project_point(req.latitude, req.longitude)
    radii_m = [round(m / 60 * URBAN_SPEED_KMH * 1000) for m in MINUTES]
    results = []
    for minutes, r in zip(MINUTES, radii_m):
        pop = comps = 0
        if store.pop_xy is not None and len(store.pop_xy):
            d = np.hypot(store.pop_xy[:, 0] - x, store.pop_xy[:, 1] - y)
            pop = int(store.pop_vals[d <= r].sum())
        if store.comp_xy is not None and len(store.comp_xy):
            dc = np.hypot(store.comp_xy[:, 0] - x, store.comp_xy[:, 1] - y)
            comps = int((dc <= r).sum())
        results.append({"minutes": minutes, "radius_km": round(r / 1000, 1),
                        "reachable_population": pop, "competitors_in_range": comps,
                        "approximate_fallback": True})

    rings = store.ring_geojson(req.latitude, req.longitude, radii_m)
    return {
        "latitude": req.latitude, "longitude": req.longitude,
        "catchments": results,
        "rings_geojson": {"type": "FeatureCollection", "features": [
            {"type": "Feature",
             "properties": {"minutes": MINUTES[i], "radius_km": round(radii_m[i] / 1000, 1)},
             "geometry": rings[i]["geometry"]}
            for i in range(len(MINUTES))
        ]},
        "method": f"approximation — straight-line travel shed at {URBAN_SPEED_KMH:.0f} km/h urban average",
        "engine": "radius-fallback",
    }
