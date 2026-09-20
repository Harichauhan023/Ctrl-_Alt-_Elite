from __future__ import annotations

from fastapi import APIRouter, HTTPException
from shapely.geometry import Point

from app.geospatial.hexgrid import hotspot_grid, score_cell
from app.geospatial.loader import get_store
from app.schemas.models import RecommendRequest
from app.scoring.config import BUSINESS_CONFIGS, get_business

router = APIRouter()


@router.post("/recommend")
def recommend(req: RecommendRequest):
    business = req.business_type.upper()
    if business not in BUSINESS_CONFIGS:
        raise HTTPException(400, f"Unknown business_type. Available: {', '.join(BUSINESS_CONFIGS)}")
    if not hotspot_grid.ready:
        raise HTTPException(503, "Hotspot grid not ready yet.")
    try:
        weights = req.weights.as_fraction() if req.weights else None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    store = get_store()
    poly = store.polygon_utm(req.polygon) if req.polygon else None

    zones = []
    for c in hotspot_grid.cells:
        if req.exclude_constrained and c["constrained"]:
            continue
        if c["population"] < req.min_population:
            continue
        if c["competitors_within_1km"] > req.max_competitors_1km:
            continue
        if poly is not None:
            x, y = store.project_point(c["lat"], c["lng"])
            if not poly.contains(Point(x, y)):
                continue
        s = score_cell(c, business, weights)
        zones.append({
            "h3": c["h3"], "latitude": c["lat"], "longitude": c["lng"],
            "overall": s["overall"], "band": s["band"], "color": s["color"],
            "scores": {f: s[f] for f in ("population", "accessibility", "competition",
                                         "land_use", "environment")},
            "competitors_within_1km": c["competitors_within_1km"],
            "land_category": c["land_category"], "risk_level": c["risk_level"],
        })
    zones.sort(key=lambda z: (-z["overall"], z["h3"]))
    return {
        "business_type": business,
        "business_label": get_business(business)["label"],
        "constraints_applied": {
            "min_population_score": req.min_population,
            "max_competitors_within_1km": req.max_competitors_1km,
            "exclude_constrained": req.exclude_constrained,
            "polygon_filter": bool(req.polygon),
        },
        "candidates_evaluated": len(hotspot_grid.cells),
        "surviving": len(zones),
        "zones": zones[: req.top_k],
    }
