"""
Deterministic rule-based explainer — PS-2 §54 Graceful AI Degradation.

Produces the SAME JSON shape as the LLM so the frontend never cares which
engine answered. This is also the primary explainer when no API keys are set.
"""
from __future__ import annotations

_LABELS = {
    "population": "nearby population",
    "accessibility": "road accessibility",
    "competition": "competitive position",
    "land_use": "land-use fit",
    "environment": "environmental conditions",
}


def deterministic_explanation(facts: dict, rag_titles: list[str] | None = None,
                              question: str | None = None) -> dict:
    scores: dict = facts.get("scores", {})
    metrics = facts.get("metrics", {})
    status = facts.get("status", "")
    overall = facts.get("overall_score", 0)
    constraints = facts.get("constraints", [])
    business = facts.get("business_label", "this business")

    ranked_hi = sorted(scores.items(), key=lambda kv: -kv[1])
    strengths: list[str] = []
    risks: list[str] = []

    for f, s in ranked_hi:
        if s >= 78 and len(strengths) < 4:
            strengths.append(_phrase(f, s, metrics, positive=True))
    for f, s in sorted(scores.items(), key=lambda kv: kv[1]):
        if s <= 55 and len(risks) < 4:
            risks.append(_phrase(f, s, metrics, positive=False))
    risks.extend(constraints)

    if status == "NOT_SUITABLE":
        summary = (
            f"This site is marked NOT SUITABLE for {business} despite a numeric readiness of "
            f"{overall}/100, because at least one hard constraint was triggered. The numeric score "
            f"still reflects underlying demand-side conditions, but the constraint overrides it."
        )
        key_reason = constraints[0] if constraints else "A hard constraint overrides the score."
    else:
        best = ranked_hi[0] if ranked_hi else ("population", 0)
        worst = ranked_hi[-1] if ranked_hi else ("environment", 0)
        summary = (
            f"With an overall readiness of {overall}/100 ({status.replace('_', ' ').title()}), this "
            f"site's profile for {business} is led by strong {_LABELS.get(best[0], best[0])} "
            f"({best[1]:.0f}/100), while {_LABELS.get(worst[0], worst[0])} ({worst[1]:.0f}/100) is the "
            f"main factor holding the score back."
        )
        key_reason = (
            f"The score is driven primarily by {_LABELS.get(best[0], best[0])} "
            f"({best[1]:.0f}/100); improve or accept the {_LABELS.get(worst[0], worst[0])} "
            f"({worst[1]:.0f}/100) before committing."
        )

    out = {"summary": summary, "strengths": strengths or ["No standout strengths — a balanced, middling profile."],
           "risks": risks or ["No material risks detected in the scored factors."],
           "key_reason": key_reason}
    if question:
        out["answer"] = (
            f"Based on the computed factors: overall {overall}/100 ({status.replace('_', ' ').title()}). "
            f"Strongest: {_LABELS.get(ranked_hi[0][0], '')} {ranked_hi[0][1]:.0f}/100. "
            f"Weakest: {_LABELS.get(ranked_hi[-1][0], '')} {ranked_hi[-1][1]:.0f}/100."
        )
    if rag_titles:
        out["sources"] = rag_titles
    return out


def _phrase(factor: str, s: float, metrics: dict, positive: bool) -> str:
    if factor == "population":
        pop = metrics.get("population_within_1km")
        return (f"{'Strong' if positive else 'Limited'} nearby population — about "
                f"{pop:,} people within 1 km" if isinstance(pop, int) else
                f"{'High' if positive else 'Low'} population score ({s:.0f}/100)")
    if factor == "accessibility":
        d = metrics.get("nearest_major_road_km")
        return (f"{'Excellent' if positive else 'Weak'} road access — nearest major road "
                f"{d} km away" if d is not None else
                f"Accessibility score {s:.0f}/100")
    if factor == "competition":
        c = metrics.get("competitors_within_1km")
        n = metrics.get("nearest_competitor_km")
        if positive:
            return f"Open competitive field — {c} competitors within 1 km (nearest {n} km)"
        return f"Crowded market — {c} competitors within 1 km (nearest {n} km)"
    if factor == "land_use":
        cat = metrics.get("land_use_category", "unknown")
        return (f"Land use ({cat}) is well suited ({s:.0f}/100)" if positive
                else f"Land use ({cat}) is a poor fit ({s:.0f}/100)")
    lvl = metrics.get("risk_level", "low")
    return (f"Low environmental exposure ({lvl})" if positive
            else f"Elevated environmental risk ({lvl}, {s:.0f}/100)")
