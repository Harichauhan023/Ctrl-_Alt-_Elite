"""H3 readiness heatmap endpoints (PS-2 §34: /api/hotspots)."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..geospatial.hexgrid import hotspot_grid
from ..scoring.config import BUSINESS_CONFIGS

router = APIRouter()


def _weights_from_query(wp, wa, wc, wl, we):
    vals = [wp, wa, wc, wl, we]
    if all(v is None for v in vals):
        return None
    if any(v is None for v in vals):
        raise HTTPException(400, "Provide all five weights (wp, wa, wc, wl, we) or none.")
    total = wp + wa + wc + wl + we
    if abs(total - 100) > 5:
        raise HTTPException(400, f"Weights must sum to 100% (got {total:.1f}%).")
    return {"population": wp / 100, "accessibility": wa / 100, "competition": wc / 100,
            "land_use": wl / 100, "environment": we / 100}


@router.get("/hotspots")
def hotspots(business_type: str = Query("EV_CHARGING"),
             wp: float | None = None, wa: float | None = None,
             wc: float | None = None, wl: float | None = None,
             we: float | None = None):
    business = business_type.upper()
    if business not in BUSINESS_CONFIGS:
        raise HTTPException(400, f"Unknown business_type. Available: {', '.join(BUSINESS_CONFIGS)}")
    if not hotspot_grid.ready:
        raise HTTPException(503, "Hotspot grid not ready yet — try again in a moment.")
    weights = _weights_from_query(wp, wa, wc, wl, we)
    fc = hotspot_grid.readiness_fc(business, weights)
    return {"business_type": business, "cells": len(fc["features"]),
            "geojson": fc, "note": "Readiness per H3 res-8 cell — deterministic, reproducible."}


@router.get("/hotspots/distribution")
def hotspot_distribution(business_type: str = Query("EV_CHARGING")):
    business = business_type.upper()
    if business not in BUSINESS_CONFIGS:
        raise HTTPException(400, "Unknown business_type.")
    if not hotspot_grid.ready:
        raise HTTPException(503, "Hotspot grid not ready yet.")
    return hotspot_grid.distribution(business, None)
