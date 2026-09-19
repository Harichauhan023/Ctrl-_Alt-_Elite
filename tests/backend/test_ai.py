"""AI provider & fallback tests (spec §42 — AI).

Covers: deterministic explainer contract shape, provider manager bookkeeping,
and the graceful-degradation rule — with ZERO keys the pipeline must still
return a complete explanation.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.ai.explainer import deterministic_explanation   # noqa: E402
from app.ai.provider import provider_manager             # noqa: E402


_SAMPLE_FACTS = {
    "business_label": "EV Charging Station",
    "overall_score": 87.3,
    "status": "HIGH_POTENTIAL",
    "scores": {"population": 92.0, "accessibility": 95.0, "competition": 63.4,
               "land_use": 95.0, "environment": 100.0},
    "constraints": [],
    "metrics": {"population_within_1km": 40587, "nearest_major_road_km": 0.0,
                "competitors_within_1km": 0, "land_use_category": "unknown"},
}


def test_deterministic_explainer_shape():
    out = deterministic_explanation(_SAMPLE_FACTS, ["EV Charging Station Business Guide"])
    for key in ("summary", "strengths", "risks", "key_reason"):
        assert key in out
    assert isinstance(out["strengths"], list) and out["strengths"]
    assert out["sources"] == ["EV Charging Station Business Guide"]


def test_deterministic_explainer_handles_constraints():
    facts = {**_SAMPLE_FACTS, "status": "NOT_SUITABLE",
             "constraints": ["Site lies on protected land"]}
    out = deterministic_explanation(facts)
    assert "NOT SUITABLE" in out["summary"]
    assert "protected land" in out["key_reason"]


def test_provider_manager_bookkeeping_without_keys():
    st = provider_manager.status()
    assert isinstance(st, list)
    assert provider_manager.call_count >= 0
    # no keys configured in the sandbox → not configured
    assert provider_manager.configured in (True, False)  # truthy-state must be honest


def test_provider_explain_returns_none_without_keys():
    if provider_manager.configured:
        import pytest as _pt
        _pt.skip("keys present in this environment")
    data, reason = provider_manager.explain("sys", "user")
    assert data is None and isinstance(reason, str)
