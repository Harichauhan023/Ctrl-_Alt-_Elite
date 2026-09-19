"""Factor scorers (0–100) — PURE functions over extracted features.

Features come from `geospatial/features.py` (real SQL spatial queries against
PostGIS/DuckDB, or the memory fallback). These functions contain the business
logic only: decay curves, component blending, polarity, hard caps. Everything
is deterministic: same features ⇒ same scores (PS-2 Rule 10).

Methodology per factor:
  population     effective population within 1.2 km, exponential decay (0.6 km)
  accessibility  60% proximity to MAJOR roads (decay) + 40% road density in 600 m
  competition    counts within 1/3 km + nearest distance; polarity avoid|attract
  land_use       category suitability per business config
  environment    worst intersecting risk polygon → level score; critical = hard stop
"""
from __future__ import annotations

import math

from .config import ENV_SCORE_MAP

POP_RADIUS_M = 1200.0
POP_DECAY_KM = 0.6
ROAD_DENSITY_RADIUS_M = 600.0
ROAD_DENSITY_REF = 9.0         # km of road per km² that maps to a perfect 100
MAJOR_ROAD_DECAY_KM = 1.2      # urban reality: 500 m from an arterial is still excellent
ANY_ROAD_HARD_CAP_KM = 5.0     # PS-2 §18 — far from ANY road ⇒ heavily capped


def population_score(fe: dict, pop_ref: float) -> tuple[float, dict]:
    eff = float(fe.get("effective_population", 0.0))
    score = min(100.0, 100.0 * eff / max(pop_ref, 1.0))
    return score, {
        "effective_population": round(eff),
        "population_within_1km": int(fe.get("population_within_1km", 0)),
        "population_within_500m": int(fe.get("population_within_500m", 0)),
        "population_within_3km": int(fe.get("population_within_3km", 0)),
        "normalisation_ref": round(pop_ref),
    }


def accessibility_score(fe: dict) -> tuple[float, dict]:
    d_major_m = float(fe.get("nearest_major_road_km", 9999.0)) * 1000.0
    d_any_km = float(fe.get("nearest_road_km", 9999.0))
    density = float(fe.get("road_density_km_per_km2", 0.0))
    prox = 100.0 * math.exp(-(d_major_m / 1000.0) / MAJOR_ROAD_DECAY_KM)
    dens_score = min(100.0, density / ROAD_DENSITY_REF * 100.0)
    score = 0.6 * prox + 0.4 * dens_score
    if d_any_km > ANY_ROAD_HARD_CAP_KM:
        score = min(score, 20.0)  # soft penalty: effectively unreachable
    return score, {
        "nearest_major_road_km": round(d_major_m / 1000.0, 2),
        "nearest_road_km": round(d_any_km, 2),
        "road_length_within_600m_km": float(fe.get("road_length_within_600m_km", 0.0)),
        "road_density_km_per_km2": round(density, 1),
        "proximity_component": round(prox, 1),
        "density_component": round(dens_score, 1),
    }


def competition_score(fe: dict, polarity: str = "avoid") -> tuple[float, dict]:
    c1 = int(fe.get("competitors_within_1km", 0))
    c3 = int(fe.get("competitors_within_3km", 0))
    nearest = fe.get("nearest_competitor_km")
    names = fe.get("nearest_competitors") or []
    simulated = int(fe.get("simulated_extra", 0))
    real_market = c1 - simulated if simulated else c1
    if c1 == 0 and c3 == 0 and nearest is None:
        return (50.0 if polarity == "attract" else 100.0), {
            "note": "0 competitors found in dataset — treated as open market",
            "competitors_within_1km": 0, "competitors_within_3km": 0,
            "nearest_competitor_km": None, "polarity": polarity,
        }
    s_near = 100.0 * math.exp(-c1 / 2.0)
    s_density = 100.0 * math.exp(-c3 / 6.0)
    s_distance = min(100.0, (nearest or 0.0) / 3.0 * 100.0)
    avoid = 0.5 * s_near + 0.3 * s_density + 0.2 * s_distance
    score = avoid if polarity == "avoid" else max(5.0, 100.0 - avoid * 0.8)
    details = {
        "competitors_within_1km": c1,
        "competitors_within_3km": c3,
        "nearest_competitor_km": round(nearest, 2) if nearest is not None else None,
        "nearest_competitors": names[:3],
        "polarity": polarity,
        "simulated_extra": simulated,
    }
    _ = real_market  # (kept for future reporting; score uses combined field)
    return score, details


def landuse_score(fe: dict, business_cfg: dict) -> tuple[float, dict]:
    category = fe.get("land_use_category", "unknown")
    value = business_cfg["landuse"].get(category, 50)
    return float(value), {"land_use_category": category}


def environment_score(fe: dict) -> tuple[float, dict]:
    level = fe.get("risk_level", "low")
    hits = fe.get("risk_hits") or []
    return float(ENV_SCORE_MAP.get(level, 100)), {
        "risk_level": level,
        "risks": hits,
    }
