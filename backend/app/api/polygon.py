"""Custom polygon area analysis (PS-2 §36).

Answers "how healthy is this whole district?" instead of one parcel:
population, road km, competitors, land/risk mix + zone readiness inside.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import shapely
from fastapi import APIRouter, HTTPException
from shapely.geometry import Point

from ..geospatial.hexgrid import hotspot_grid, score_cell
from ..geospatial.loader import get_store
from ..schemas.models import PolygonAnalyzeRequest
from ..scoring.config import BUSINESS_CONFIGS, get_business

router = APIRouter()


@router.post("/polygon")
def polygon_analyze(req: PolygonAnalyzeRequest):
    business = req.business_type.upper()
    if business not in BUSINESS_CONFIGS:
        raise HTTPException(400, f"Unknown business_type. Available: {', '.join(BUSINESS_CONFIGS)}")
    if not hotspot_grid.ready:
        raise HTTPException(503, "Grid not ready.")
    try:
        weights = req.weights.as_fraction() if req.weights else None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    store = get_store()
    poly = store.polygon_utm(req.polygon)
    if poly.area <= 0:
        raise HTTPException(400, "Polygon area is zero — draw a bigger area.")
    area_km2 = poly.area / 1e6

    # population (res-9 centroid containment)
    pop_total = 0
    if store.pop_xy is not None and len(store.pop_xy):
        m = shapely.contains_xy(poly, store.pop_xy[:, 0], store.pop_xy[:, 1])
        pop_total = int(store.pop_vals[m].sum()) if m.any() else 0
    # road km (true line∩polygon)
    road_km = 0.0
    if store.road_geoms is not None and len(store.road_geoms):
        road_km = float(np.sum(shapely.length(shapely.intersection(poly, store.road_geoms)))) / 1000.0
    # competitors
    comps_in = 0
    if store.comp_xy is not None and len(store.comp_xy):
        mc = shapely.contains_xy(poly, store.comp_xy[:, 0], store.comp_xy[:, 1])
        comps_in = int(mc.sum()) if mc.any() else 0

    cells = []
    for c in hotspot_grid.cells:
        x, y = store.project_point(c["lat"], c["lng"])
        if poly.contains(Point(x, y)):
            s = score_cell(c, business, weights)
            cells.append({"h3": c["h3"], "latitude": c["lat"], "longitude": c["lng"],
                          "overall": s["overall"], "band": s["band"], "color": s["color"],
                          "land_category": c["land_category"], "risk_level": c["risk_level"],
                          "constrained": c["constrained"],
                          "competitors_within_1km": c["competitors_within_1km"]})

    land_mix = Counter(c["land_category"] for c in cells)
    risk_mix = Counter(c["risk_level"] for c in cells)
    band_mix = Counter(c["band"] for c in cells)
    overalls = [c["overall"] for c in cells]
    mean = round(float(np.mean(overalls)), 1) if overalls else 0.0
    constrained_share = round(100 * sum(1 for c in cells if c["constrained"]) / len(cells), 1) if cells else 0
    top_cells = sorted(cells, key=lambda c: -c["overall"])[:5]
    label = get_business(business)["label"]

    return {
        "business_type": business,
        "business_label": label,
        "area_km2": round(area_km2, 2),
        "population": pop_total,
        "population_per_km2": round(pop_total / area_km2) if area_km2 else 0,
        "road_km": round(road_km, 1),
        "road_density_km_per_km2": round(road_km / area_km2, 1) if area_km2 else 0,
        "competitors": comps_in,
        "zones": {
            "count": len(cells), "readiness_mean": mean,
            "readiness_min": min(overalls) if overalls else 0,
            "readiness_max": max(overalls) if overalls else 0,
            "bands": dict(band_mix), "constrained_share_pct": constrained_share,
        },
        "land_use_mix": dict(land_mix),
        "risk_mix": dict(risk_mix),
        "top_cells": top_cells,
        "verdict": _verdict(mean, cells, pop_total, comps_in, road_km, area_km2,
                            constrained_share, label),
        "method": "aggregation over H3 zone centroids + true geometry intersections",
    }


def _verdict(mean, cells, pop_total, comps, road_km, area_km2, constrained_share, label):
    if not cells:
        return ["No analysis zones inside this area — draw over the urban extent."]
    lines = []
    if mean >= 80:
        lines.append(f"🟢 HIGH-potential district for {label} — mean zone readiness {mean}/100.")
    elif mean >= 65:
        lines.append(f"🟢 GOOD district for {label} — mean zone readiness {mean}/100.")
    elif mean >= 50:
        lines.append(f"🟡 MODERATE district for {label} — mean {mean}/100; site selection matters street by street.")
    else:
        lines.append(f"🔴 WEAK district for {label} — mean {mean}/100; examine factors before investing.")
    if pop_total:
        lines.append(f"Modelled population in area ≈ {pop_total:,} people "
                     f"({road_km:.1f} km of roads, {comps} competitors detected).")
    if constrained_share > 0:
        lines.append(f"⚠ {constrained_share}% of area cells are hard-constrained (protected / critical risk) — exclude them from any build plan.")
    best = max(cells, key=lambda c: c["overall"])
    lines.append(f"Best pocket: zone {best['h3'][-6:]} at {best['overall']}/100 — fly to it and run a point analysis.")
    return lines
