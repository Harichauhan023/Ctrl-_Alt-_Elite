"""Documented label formula for the synthetic training set (spec §9).

We do NOT pretend synthetic labels are real-world truth. The training target
is a transparent planning-style baseline rubric applied to REAL extracted
features, plus small Gaussian noise to make the learning task honest:

    pop_s  = min(100, 100 · effective_population / POP_REF)      (decay mass)
    acc_s  = 0.6·proximity_component + 0.4·density_component     (major roads)
    comp_s = 0.5·exp(−c1/2) + 0.3·exp(−c3/6) + 0.2·min(1, nearest/3km)  ·100
    land_s = NEUTRAL_LANDUSE[category]
    env_s  = ENV_SCORE[risk_level]

    target = 0.25·pop_s + 0.25·acc_s + 0.20·comp_s + 0.15·land_s + 0.15·env_s
             + ε,  ε ~ N(0, 2.2)
    target clipped to [1, 99]
    if hard constraint (protected land / critical risk): target ×= 0.15

The ML model therefore learns the non-linear interaction structure behind a
rubric, and its holdout metrics tell us how well the surrogate fits — exactly
the honest demonstration the hackathon asks for.
"""
from __future__ import annotations

import math

from .feature_schema import ENV_SCORE, NEUTRAL_LANDUSE

WEIGHTS = {"pop": 0.25, "acc": 0.25, "comp": 0.20, "land": 0.15, "env": 0.15}
NOISE_SIGMA = 2.2
MAJOR_ROAD_DECAY_KM = 1.2
ROAD_DENSITY_REF = 9.0


def components(fe: dict, pop_ref: float) -> dict:
    eff = float(fe.get("effective_population", 0.0))
    pop_s = min(100.0, 100.0 * eff / max(pop_ref, 1.0))

    d_major = float(fe.get("nearest_major_road_km", 9999.0))
    density = float(fe.get("road_density_km_per_km2", 0.0))
    prox = 100.0 * math.exp(-d_major / MAJOR_ROAD_DECAY_KM)
    dens = min(100.0, density / ROAD_DENSITY_REF * 100.0)
    acc_s = 0.6 * prox + 0.4 * dens

    c1 = float(fe.get("competitors_within_1km", 0))
    c3 = float(fe.get("competitors_within_3km", 0))
    nearest = fe.get("nearest_competitor_km")
    if nearest is None and c1 == 0 and c3 == 0:
        comp_s = 100.0
    else:
        comp_s = (0.5 * math.exp(-c1 / 2.0) + 0.3 * math.exp(-c3 / 6.0)
                  + 0.2 * min(1.0, (nearest or 0.0) / 3.0)) * 100.0

    land_s = NEUTRAL_LANDUSE.get(fe.get("land_use_category", "unknown"), 50.0)
    env_s = ENV_SCORE.get(fe.get("risk_level", "low"), 100.0)
    return {"pop": pop_s, "acc": acc_s, "comp": comp_s, "land": land_s, "env": env_s}


def constrained(fe: dict) -> bool:
    return (fe.get("land_use_category") == "protected"
            or fe.get("risk_level") == "critical")


def label(fe: dict, pop_ref: float, rng) -> float:
    c = components(fe, pop_ref)
    base = sum(WEIGHTS[k] * c[k] for k in WEIGHTS)
    y = base + rng.normal(0.0, NOISE_SIGMA)
    if constrained(fe):
        y *= 0.15
    return min(99.0, max(1.0, y))
