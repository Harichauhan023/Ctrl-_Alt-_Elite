"""Geospatial feature extraction tests (spec §42 — geospatial).

Covers: distance calculation, point-in-polygon, competitor radius,
land-use lookup, risk lookup — on the SQL path (DuckDB) with parity
checks against the memory path.
"""
import pytest

from app.geospatial.features import MemoryExtractor, SQLExtractor

POINTS = {
    "astron": (22.2903, 70.7655),
    "center": (22.3039, 70.8022),
    "river": (22.2830, 70.7930),
    "greenland": (22.3310, 70.7690),
}


@pytest.fixture(scope="module")
def sql(tmp_geodb):
    return SQLExtractor(tmp_geodb)


@pytest.fixture(scope="module")
def mem(store):
    return MemoryExtractor(store)


def _xy(store, name):
    return store.project_point(*POINTS[name])


# ── land-use lookup (point-in-polygon) ─────────────────────────────────────
def test_landuse_lookup_sql(store, sql):
    assert sql.extract(*_xy(store, "astron"))["land_use_category"] == "commercial"
    assert sql.extract(*_xy(store, "river"))["land_use_category"] == "protected"
    assert sql.extract(*_xy(store, "greenland"))["land_use_category"] == "residential"


# ── risk lookup (worst-of containment) ─────────────────────────────────────
def test_risk_lookup_sql(store, sql):
    assert sql.extract(*_xy(store, "river"))["risk_level"] == "critical"
    assert sql.extract(*_xy(store, "greenland"))["risk_level"] == "low"
    hits = sql.extract(*_xy(store, "river"))["risk_hits"]
    assert hits and all("risk_type" in h for h in hits)


# ── competitor radius (1km) ────────────────────────────────────────────────
def test_competitor_radius_sql(store, sql):
    assert sql.extract(*_xy(store, "astron"))["competitors_within_1km"] >= 1
    assert sql.extract(*_xy(store, "center"))["competitors_within_1km"] == 0


# ── distance calculation ───────────────────────────────────────────────────
def test_distance_calculation_sql(store, sql):
    fe = sql.extract(*_xy(store, "center"))
    assert 0 <= fe["nearest_major_road_km"] < 0.5          # on top of Ring Road
    assert fe["nearest_competitor_km"] is None or fe["nearest_competitor_km"] > 0
    names = fe["nearest_competitors"]
    assert all(name["distance_km"] >= 0 for name in names)


# ── population radii (SQL aggregates) ──────────────────────────────────────
def test_population_radii_sql(store, sql):
    fe = sql.extract(*_xy(store, "astron"))
    assert fe["population_within_1km"] > 40000
    assert fe["population_within_500m"] <= fe["population_within_1km"]
    assert fe["population_within_1km"] <= fe["population_within_3km"]
    assert fe["effective_population"] > 0


# ── SQL-vs-memory parity (the dual-path contract) ──────────────────────────
def test_sql_memory_parity(store, sql, mem):
    for name in POINTS:
        xy = _xy(store, name)
        a = sql.extract(*xy)
        b = mem.extract(*xy)
        assert a["land_use_category"] == b["land_use_category"], name
        assert a["risk_level"] == b["risk_level"], name
        assert a["population_within_1km"] == b["population_within_1km"], name
        assert a["competitors_within_1km"] == b["competitors_within_1km"], name
        # buffer-segment resolution may differ marginally between engines
        assert abs(a["road_density_km_per_km2"] - b["road_density_km_per_km2"]) < 0.6, name
