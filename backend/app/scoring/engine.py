
from __future__ import annotations

from app.geospatial.features import apply_ghosts, get_extractor
from app.geospatial.loader import DataStore
from app.scoring import factors
from app.scoring.config import get_business, status_for

FACTORS = ["population", "accessibility", "competition", "land_use", "environment"]

FACTOR_LABELS = {
    "population": "Nearby population",
    "accessibility": "Road accessibility",
    "competition": "Competitive pressure",
    "land_use": "Land-use suitability",
    "environment": "Environmental risk",
}

REASON_TEMPLATES = {
    "population": ("Strong nearby population base", "Thin nearby population"),
    "accessibility": ("Excellent road accessibility", "Weak road access"),
    "competition": ("Low direct competitor pressure", "Heavy competitor density nearby"),
    "land_use": ("Land use well suited for this business", "Sub-optimal land-use zoning"),
    "environment": ("Low environmental risk", "Elevated environmental risk"),
}


def validate_weights(weights: dict) -> dict:
    missing = [f for f in FACTORS if f not in weights]
    if missing:
        raise ValueError(f"Weights missing factors: {', '.join(missing)}")
    total = sum(float(weights[f]) for f in FACTORS)
    if abs(total - 1.0) > 0.051:
        raise ValueError(f"Weights must sum to 100% (got {total*100:.1f}%).")
    return {f: float(weights[f]) / total for f in FACTORS}


def analyze(lat: float, lng: float, business_type: str, store: DataStore,
            weights: dict | None = None, name: str | None = None,
            extra_competitors: list[tuple[float, float]] | None = None,
            extractor=None, ml_service=None,
            _features: dict | None = None) -> dict:
    """extra_competitors: list of (lat, lng) what-if ghost rivals (scenario mode).
    _features: reuse an already-extracted feature vector (analyze_all efficiency)."""
    cfg = get_business(business_type)  # raises KeyError if unknown
    w = validate_weights(weights or cfg["weights"])
    x, y = store.project_point(lat, lng)
    extractor = extractor or get_extractor()

    fe = dict(_features) if _features else extractor.extract(x, y)
    ghost_xy = None
    if extra_competitors:
        ghost_xy = [store.project_point(la, ln) for la, ln in extra_competitors]
        fe = apply_ghosts(fe, ghost_xy, x, y)

    pop_s, pop_d = factors.population_score(fe, store.pop_ref)
    acc_s, acc_d = factors.accessibility_score(fe)
    cmp_s, cmp_d = factors.competition_score(fe, cfg["competition_polarity"])
    lnd_s, lnd_d = factors.landuse_score(fe, cfg)
    env_s, env_d = factors.environment_score(fe)

    scores = {"population": round(pop_s, 1), "accessibility": round(acc_s, 1),
              "competition": round(cmp_s, 1), "land_use": round(lnd_s, 1),
              "environment": round(env_s, 1)}

    constraints = []
    if lnd_d.get("land_use_category") == "protected":
        constraints.append("Site lies on protected land (lake / river corridor) — development not permitted")
    if env_d.get("risk_level") == "critical":
        constraints.append("Site lies in a CRITICAL flood-risk pocket — site invalidated")

    overall = round(sum(scores[f] * w[f] for f in FACTORS), 1)
    status = "NOT_SUITABLE" if constraints else status_for(overall)

    reasons, risks = build_reasons(scores, cmp_d, lnd_d, env_d, cfg, constraints)

    ml = None
    if ml_service is None:
        try:
            from app.services.ml_service import get_ml_service
            ml_service = get_ml_service()
        except Exception:
            ml_service = None
    if ml_service is not None and ml_service.available:
        try:
            ml = ml_service.predict(fe)
        except Exception:
            ml = None

    return {
        "name": name,
        "latitude": lat, "longitude": lng,
        "business_type": business_type,
        "business_label": cfg["label"],
        "overall_score": overall,
        "status": status,
        "scores": scores,
        "weights": {f: round(w[f], 4) for f in FACTORS},
        "details": {"population": pop_d, "accessibility": acc_d, "competition": cmp_d,
                    "land_use": lnd_d, "environment": env_d},
        "constraints": constraints,
        "reasons": reasons,
        "risks": risks,
        "ml_prediction": ml,
        "ml_available": ml is not None,
        "feature_mode": getattr(extractor, "mode", "memory"),
        "ml_features": ml_service.feature_vector(fe) if (ml_service and ml_service.available) else None,
    }


def build_reasons(scores, cmp_d, lnd_d, env_d, cfg, constraints):
    reasons, risks = [], []
    for f in FACTORS:
        pos, neg = REASON_TEMPLATES[f]
        if f == "competition" and cfg["competition_polarity"] == "attract":
            if scores[f] >= 70:
                reasons.append("Active commercial cluster validates market demand")
            elif scores[f] <= 40:
                risks.append("Little existing commercial activity nearby")
            continue
        if scores[f] >= 78:
            extra = ""
            if f == "land_use":
                extra = f" ({lnd_d.get('land_use_category')})"
            reasons.append(f"{pos} — {scores[f]:.0f}/100{extra}")
        elif scores[f] <= 55:
            extra = ""
            if f == "land_use":
                extra = f" ({lnd_d.get('land_use_category')})"
            elif f == "environment":
                extra = f" ({env_d.get('risk_level')})"
            elif f == "competition":
                extra = f" ({cmp_d.get('competitors_within_1km', 0)} within 1 km)"
            risks.append(f"{neg}{extra}")
    for c in constraints:
        risks.append(c)
    return reasons[:4], risks[:4]


def facts_for_llm(result: dict) -> dict:
    d = result.get("details", {})
    return {
        "site_name": result.get("name") or "Candidate pin",
        "business_type": result.get("business_type"),
        "business_label": result.get("business_label"),
        "location": {"lat": result.get("latitude"), "lng": result.get("longitude")},
        "overall_score": result.get("overall_score"),
        "ml_prediction": result.get("ml_prediction"),
        "score_ml_delta": (round(result["overall_score"] - result["ml_prediction"], 1)
                           if result.get("ml_prediction") is not None else None),
        "status": result.get("status"),
        "scores": result.get("scores"),
        "weights": result.get("weights"),
        "constraints": result.get("constraints", []),
        "metrics": {
            "population_within_1km": d.get("population", {}).get("population_within_1km"),
            "nearest_major_road_km": d.get("accessibility", {}).get("nearest_major_road_km"),
            "road_density_km_per_km2": d.get("accessibility", {}).get("road_density_km_per_km2"),
            "competitors_within_1km": d.get("competition", {}).get("competitors_within_1km"),
            "competitors_within_3km": d.get("competition", {}).get("competitors_within_3km"),
            "nearest_competitor_km": d.get("competition", {}).get("nearest_competitor_km"),
            "land_use_category": d.get("land_use", {}).get("land_use_category"),
            "risk_level": d.get("environment", {}).get("risk_level"),
        },
        "reasons": result.get("reasons", []),
        "risks": result.get("risks", []),
    }
