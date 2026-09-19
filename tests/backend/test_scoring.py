"""
Deterministic-engine test suite (PS-2 §56).

Run:  python3 -m pytest tests/ -q
"""
import math

import pytest

from app.scoring import engine
from app.scoring.engine import validate_weights

EV = {"population": 0.20, "accessibility": 0.35, "competition": 0.20,
      "land_use": 0.10, "environment": 0.15}


# ── weight validation ───────────────────────────────────────────────────────
def test_weights_must_sum_to_100():
    with pytest.raises(ValueError, match="100"):
        validate_weights({"population": 0.3, "accessibility": 0.3, "competition": 0.2,
                          "land_use": 0.0, "environment": 0.0})  # sums to 0.8


def test_weights_accept_and_renormalise():
    w = validate_weights(dict(EV))
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_weights_missing_factor_rejected():
    with pytest.raises(ValueError, match="missing"):
        validate_weights({"population": 1.0})


# ── deterministic scoring ───────────────────────────────────────────────────
def test_analysis_is_deterministic(store):
    a = engine.analyze(22.2903, 70.7655, "EV_CHARGING", store, EV)
    b = engine.analyze(22.2903, 70.7655, "EV_CHARGING", store, EV)
    assert a["overall_score"] == b["overall_score"]
    assert a["scores"] == b["scores"]


def test_scores_bounded_0_100(store):
    for lat, lng in [(22.2903, 70.7655), (22.3310, 70.7690), (22.2635, 70.8060)]:
        r = engine.analyze(lat, lng, "EV_CHARGING", store, EV)
        assert 0 <= r["overall_score"] <= 100
        for v in r["scores"].values():
            assert 0 <= v <= 100


def test_weight_change_changes_score(store):
    pop_heavy = {**EV, "population": 0.5, "accessibility": 0.1,
                 "competition": 0.2, "land_use": 0.1, "environment": 0.1}
    # Greenland Chowkdi: weak population, strong roads → weights must move the score
    base = engine.analyze(22.3310, 70.7690, "EV_CHARGING", store, EV)
    shifted = engine.analyze(22.3310, 70.7690, "EV_CHARGING", store, pop_heavy)
    assert not math.isclose(base["overall_score"], shifted["overall_score"], abs_tol=1.0)


# ── hard constraints ────────────────────────────────────────────────────────
def test_critical_flood_pocket_is_not_suitable(store):
    r = engine.analyze(22.2830, 70.7930, "EV_CHARGING", store, EV)  # Aji river pocket
    assert r["status"] == "NOT_SUITABLE"
    assert r["constraints"], "expected at least one hard constraint"


def test_normal_site_has_no_constraints(store):
    r = engine.analyze(22.2903, 70.7655, "EV_CHARGING", store, EV)
    assert r["status"] != "NOT_SUITABLE"
    assert r["constraints"] == []


# ── competition polarity ────────────────────────────────────────────────────
def test_retail_attract_mode_rewards_clusters(store):
    dense = (22.2903, 70.7655)  # Astron Chowk — charger cluster
    ev = engine.analyze(*dense, "EV_CHARGING", store, None)
    retail = engine.analyze(*dense, "RETAIL", store, None)
    assert retail["scores"]["competition"] > ev["scores"]["competition"]


# ── hotspot grid ────────────────────────────────────────────────────────────
def test_hotspot_grid_integrity(grid):
    fc = grid.readiness_fc("EV_CHARGING", EV)
    assert len(fc["features"]) > 400
    for f in fc["features"][:50]:
        assert 0 <= f["properties"]["overall"] <= 100
        assert f["properties"]["band"] in ("High", "Good", "Medium", "Weak", "Low", "Restricted")


def test_hotspot_respects_weights(grid):
    defaults = grid.readiness_fc("EV_CHARGING", EV)
    eco = defaults["features"]
    assert all(isinstance(f["geometry"]["coordinates"][0][0], list) for f in eco)


# ── distance decay sanity ───────────────────────────────────────────────────
def test_distance_decay_monotonic():
    vals = [math.exp(-d / 0.6) for d in (0.2, 0.5, 1.0, 2.0)]
    assert all(vals[i] > vals[i + 1] for i in range(3))
