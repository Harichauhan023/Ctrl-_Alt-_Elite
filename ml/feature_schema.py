"""ML input feature schema — the single source of truth (spec §8).

The trained model consumes geospatial features computed by the BACKEND
pipeline (backend/app/geospatial/features.py — real SQL spatial queries).
Order here == column order in training_data.csv == input order of model.

Feature derivations from the canonical feature dict (`fe`):
  population_1km            people within 1 km (res-9 cell containment sum)
  population_3km            people within 3 km
  population_density        population_1km / π  (persons per km²)
  nearest_major_road_km     distance to motorway/trunk/primary/secondary
  road_density              km of road per km² inside a 600 m disc
  competitors_1km           competitor count within 1 km
  competitors_3km           competitor count within 3 km
  nearest_competitor_km     distance to nearest competitor (None → 5.0 cap)
  landuse_score             neutral suitability = MEAN of the category's
                            suitability across the six business configs
                            (business-agnostic by design — deterministic
                            layer applies business-specific judgement)
  environment_risk_score    100/60/20/0 for low/medium/high/critical
  catchment_population_*m   people within 10/20/30-min travel sheds
                            (18 km/h urban proxy radii)
"""
from __future__ import annotations

FEATURES: list[str] = [
    "population_1km",
    "population_3km",
    "population_density",
    "nearest_major_road_km",
    "road_density",
    "competitors_1km",
    "competitors_3km",
    "nearest_competitor_km",
    "landuse_score",
    "environment_risk_score",
    "catchment_population_10m",
    "catchment_population_20m",
    "catchment_population_30m",
]

# neutral suitability = mean of per-business suitability values
# (verified against backend scoring/config.py by tests/test_ml.py)
NEUTRAL_LANDUSE = {
    "commercial": 75.8, "mixed_use": 73.3, "industrial": 75.0,
    "residential": 49.2, "agricultural": 44.2, "protected": 0.0, "unknown": 50.0,
}

ENV_SCORE = {"low": 100.0, "medium": 60.0, "high": 20.0, "critical": 0.0}

NEAREST_COMP_CAP_KM = 5.0


def vector_from_features(fe: dict) -> list[float]:
    """Canonical feature dict → ordered model input vector."""
    cat = fe.get("land_use_category", "unknown")
    nearest = fe.get("nearest_competitor_km")
    return [
        float(fe.get("population_within_1km", 0)),
        float(fe.get("population_within_3km", 0)),
        float(fe.get("population_density_1km", 0.0)),
        min(float(fe.get("nearest_major_road_km", 9999.0)), 20.0),
        float(fe.get("road_density_km_per_km2", 0.0)),
        float(fe.get("competitors_within_1km", 0)),
        float(fe.get("competitors_within_3km", 0)),
        min(float(nearest), NEAREST_COMP_CAP_KM) if nearest is not None else NEAREST_COMP_CAP_KM,
        NEUTRAL_LANDUSE.get(cat, 50.0),
        ENV_SCORE.get(fe.get("risk_level", "low"), 100.0),
        float(fe.get("catchment_population_10m", 0)),
        float(fe.get("catchment_population_20m", 0)),
        float(fe.get("catchment_population_30m", 0)),
    ]


def named_vector_from_features(fe: dict) -> dict:
    return {name: round(v, 4) for name, v in zip(FEATURES, vector_from_features(fe))}
