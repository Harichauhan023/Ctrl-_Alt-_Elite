from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.geospatial.loader import get_store
from app.schemas.models import AnalyzeRequest, CompareRequest
from app.scoring import engine
from app.scoring.config import BUSINESS_CONFIGS, get_business

router = APIRouter()


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    store = get_store()
    try:
        weights = req.weights.as_fraction() if req.weights else None
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    extra = [(c.latitude, c.longitude) for c in (req.extra_competitors or [])][:10] or None
    try:
        return engine.analyze(req.latitude, req.longitude, req.business_type.upper(),
                              store, weights, name=req.name, extra_competitors=extra)
    except KeyError as exc:
        raise HTTPException(
            400, f"Unknown business_type '{req.business_type}'. "
                 f"Available: {', '.join(BUSINESS_CONFIGS)}") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/analyze_all")
def analyze_all(req: AnalyzeRequest):
    """One pin, every business type (with each type's own default weights)."""
    store = get_store()
    extra = [(c.latitude, c.longitude) for c in (req.extra_competitors or [])][:10] or None
    out = {}
    for key in BUSINESS_CONFIGS:
        out[key] = engine.analyze(req.latitude, req.longitude, key, store, None,
                                  name=req.name, extra_competitors=extra)
    return {"latitude": req.latitude, "longitude": req.longitude,
            "name": req.name, "results": out}


@router.post("/compare")
def compare(req: CompareRequest):
    store = get_store()
    try:
        weights = req.weights.as_fraction() if req.weights else None
        business = req.business_type.upper()
        get_business(business)
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc

    results = []
    for i, p in enumerate(req.points):
        r = engine.analyze(p.latitude, p.longitude, business, store, weights,
                           name=p.name or f"Site {chr(65 + i)}")
        results.append(r)

    # winners per factor + overall
    winners: dict[str, str] = {}
    for f in engine.FACTORS:
        best = max(results, key=lambda r: r["scores"][f])
        winners[f] = best["name"]
    winners["overall"] = max(results, key=lambda r: r["overall_score"])["name"]

    narrative = _compare_narrative(results, winners)
    return {"business_type": business, "results": results, "winners": winners,
            "narrative": narrative}


def _compare_narrative(results: list[dict], winners: dict) -> list[str]:
    lines = []
    lead = winners["overall"]
    lead_r = next(r for r in results if r["name"] == lead)
    worst = min(results, key=lambda r: r["overall_score"])
    gap = round(lead_r["overall_score"] - worst["overall_score"], 1)
    lines.append(f"{lead} leads overall at {lead_r['overall_score']}/100, "
                 f"{gap} points ahead of {worst['name']} ({worst['overall_score']}).")
    factor_wins = {r["name"]: sum(1 for f in engine.FACTORS if winners[f] == r["name"])
                   for r in results}
    dominant = max(factor_wins, key=factor_wins.get)
    lines.append(f"{dominant} wins {factor_wins[dominant]}/5 individual factors.")
    spreads = {f: round(max(r["scores"][f] for r in results) -
                        min(r["scores"][f] for r in results), 1) for f in engine.FACTORS}
    widest = max(spreads, key=spreads.get)
    lines.append(f"The biggest differentiator is {widest.replace('_', ' ')} "
                 f"({spreads[widest]:.0f}-point spread between sites).")
    unsuitable = [r["name"] for r in results if r["status"] == "NOT_SUITABLE"]
    if unsuitable:
        lines.append(f"⚠ Hard constraints triggered at: {', '.join(unsuitable)} — "
                     "numeric scores are overridden there.")
    return lines
