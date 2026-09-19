"""Feature extraction — the geospatial truth layer.

Given (lat, lng), every number the system reasons about is produced HERE, by
real SQL spatial queries (PostGIS or DuckDB-spatial, same dialect over UTM
meters): populations within radii + exponential-decay mass, road distances &
density via line∩buffer length, competitor counts, land-use/risk containment,
and travel-time catchment proxies.

Consumers:
  • scoring/engine.py          → factor scores for one site
  • geospatial/hexgrid.py      → 649-cell hotspot grid (batched extraction)
  • geospatial/routing.py      → catchment populations
  • scripts/generate_training_data.py → 10k ML training candidates (batched)

Degradation chain (never bricks): postgis → duckdb → in-memory shapely.
`mode` tells consumers which path answered.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Point

from ..db.engine import GeoDB
from .loader import DataStore

POP_DECAY_M = 600.0          # exp decay scale (0.6 km)
POP_RADIUS_M = 1200.0
ROAD_DENSITY_RADIUS_M = 600.0
CATCHMENT_RADII_M = (3000.0, 6000.0, 9000.0)   # 10/20/30 min @ 18 km/h

_LU_PRIORITY_SQL = ("CASE category WHEN 'protected' THEN 0 WHEN 'commercial' THEN 1"
                    " WHEN 'mixed_use' THEN 2 WHEN 'industrial' THEN 3"
                    " WHEN 'residential' THEN 4 WHEN 'agricultural' THEN 5 ELSE 9 END")
_LU_PRIORITY = {"protected": 0, "commercial": 1, "mixed_use": 2, "industrial": 3,
                "residential": 4, "agricultural": 5}


def _values_pts(pts: list[tuple[int, float, float]]) -> str:
    return ",".join(f"({i},{x:.2f},{y:.2f})" for i, x, y in pts)


class SQLExtractor:
    """Primary path: everything computed by SQL in the spatial DB."""

    def __init__(self, db: GeoDB):
        self.db = db
        self.mode = db.mode

    # ── single point → batch(1) (+ nearest competitor names) ─────────────
    def extract(self, x: float, y: float) -> dict:
        fe = self.extract_batch([(x, y)])[0]
        fe["nearest_competitors"] = self._nearest_competitors(x, y)
        return fe

    def _nearest_competitors(self, x: float, y: float) -> list[dict]:
        try:
            rows = self.db.q(
                f"SELECT name, ST_Distance(geom, ST_Point({x:.2f},{y:.2f})) / 1000.0 AS d_km"
                f" FROM competitors ORDER BY d_km LIMIT 3")
            return [{"name": n, "distance_km": round(float(d), 2)} for n, d in rows]
        except Exception:
            return []

    # ── batched extraction (VALUES join per table) ────────────────────────
    def extract_batch(self, pts_xy: list[tuple[float, float]],
                      chunk: int = 400) -> list[dict]:
        n = len(pts_xy)
        out = [_empty_features() for _ in range(n)]
        for lo in range(0, n, chunk):
            idx = list(range(lo, min(lo + chunk, n)))
            pts = [(i - lo, pts_xy[i][0], pts_xy[i][1]) for i in idx]
            vals = _values_pts(pts)
            self._pop_pass(vals, idx, out)
            self._road_pass(vals, idx, out)
            self._comp_pass(vals, idx, out)
            self._landuse_pass(vals, idx, out)
            self._risk_pass(vals, idx, out)
        return out

    def _with_pts(self, body: str, vals: str) -> str:
        return f"WITH pts(i, gx, gy) AS (VALUES {vals}) {body}"

    def _pop_pass(self, vals, idx, out):
        sql = self._with_pts(
            """SELECT p.i,
                COALESCE(SUM(c.population) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 500), 0),
                COALESCE(SUM(c.population) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 1000), 0),
                COALESCE(SUM(c.population) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 1200), 0),
                COALESCE(SUM(c.population) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 3000), 0),
                COALESCE(SUM(c.population * EXP(-ST_Distance(c.geom, ST_Point(p.gx, p.gy)) / 600.0))
                   FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 1200), 0),
                COALESCE(SUM(c.population) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 6000), 0),
                COALESCE(SUM(c.population) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 9000), 0)
             FROM pts p
             JOIN (SELECT population, geom FROM population_cells) c
               ON ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 9000
             GROUP BY p.i""", vals)
        for row in self.db.q(sql):
            i, p500, p1k, p12k, p3k, eff, c20, c30 = row
            j = idx[int(i)]
            out[j]["population_within_500m"] = int(p500)
            out[j]["population_within_1km"] = int(p1k)
            out[j]["population_within_1200m"] = int(p12k)
            out[j]["population_within_3km"] = int(p3k)
            out[j]["effective_population"] = float(eff)
            out[j]["population_density_1km"] = round(float(p1k) / math.pi, 1)
            out[j]["catchment_population_10m"] = int(p3k)
            out[j]["catchment_population_20m"] = int(c20)
            out[j]["catchment_population_30m"] = int(c30)

    def _road_pass(self, vals, idx, out):
        sql = self._with_pts(
            """SELECT p.i,
                MIN(ST_Distance(r.geom, ST_Point(p.gx, p.gy))) FILTER (WHERE r.major),
                MIN(ST_Distance(r.geom, ST_Point(p.gx, p.gy)))
             FROM pts p CROSS JOIN roads r GROUP BY p.i""", vals)
        for i, dmaj, dany in self.db.q(sql):
            j = idx[int(i)]
            out[j]["nearest_major_road_km"] = round((dmaj or dany or 9999) / 1000.0, 3)
            out[j]["nearest_road_km"] = round((dany or 9999) / 1000.0, 3)
        sql2 = self._with_pts(
            f"""SELECT p.i, COALESCE(SUM(ST_Length(ST_Intersection(r.geom,
                 ST_Buffer(ST_Point(p.gx, p.gy), {ROAD_DENSITY_RADIUS_M})))), 0.0)
             FROM pts p JOIN roads r
               ON ST_DWithin(r.geom, ST_Point(p.gx, p.gy), {ROAD_DENSITY_RADIUS_M})
             GROUP BY p.i""", vals)
        for i, length_m in self.db.q(sql2):
            j = idx[int(i)]
            length_km = float(length_m or 0.0) / 1000.0
            out[j]["road_length_within_600m_km"] = round(length_km, 3)
            out[j]["road_density_km_per_km2"] = round(
                length_km / (math.pi * (ROAD_DENSITY_RADIUS_M / 1000.0) ** 2), 2)

    def _comp_pass(self, vals, idx, out):
        sql = self._with_pts(
            """SELECT p.i,
                COUNT(*) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 1000),
                COUNT(*) FILTER (WHERE ST_Distance(c.geom, ST_Point(p.gx, p.gy)) <= 3000),
                MIN(ST_Distance(c.geom, ST_Point(p.gx, p.gy)))
             FROM pts p CROSS JOIN competitors c GROUP BY p.i""", vals)
        for i, c1, c3, d in self.db.q(sql):
            j = idx[int(i)]
            out[j]["competitors_within_1km"] = int(c1 or 0)
            out[j]["competitors_within_3km"] = int(c3 or 0)
            out[j]["nearest_competitor_km"] = round(float(d), 3) if d is not None else None

    def _landuse_pass(self, vals, idx, out):
        sql = self._with_pts(
            """SELECT p.i, l.category FROM pts p
             JOIN landuse l ON ST_Contains(l.geom, ST_Point(p.gx, p.gy))""", vals)
        best: dict[int, tuple[int, str]] = {}
        for i, cat in self.db.q(sql):
            pr = _LU_PRIORITY.get(cat, 9)
            if i not in best or pr < best[i][0]:
                best[i] = (pr, cat)
        for i, (_, cat) in best.items():
            out[idx[int(i)]]["land_use_category"] = cat

    def _risk_pass(self, vals, idx, out):
        sql = self._with_pts(
            """SELECT p.i, r.risk_type, r.risk_level FROM pts p
             JOIN risk_zones r ON ST_Contains(r.geom, ST_Point(p.gx, p.gy))""", vals)
        hits: dict[int, list[dict]] = {}
        for i, rt, lvl in self.db.q(sql):
            hits.setdefault(i, []).append({"risk_type": rt, "risk_level": lvl})
        rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        for i, hs in hits.items():
            worst = max(hs, key=lambda h: rank.get(h["risk_level"], 0))
            out[idx[int(i)]]["risk_level"] = worst["risk_level"]
            out[idx[int(i)]]["risk_hits"] = hs


class MemoryExtractor:
    """Last-resort path: identical semantics computed with shapely arrays.
    Used only when no database could be initialised at all."""

    mode = "memory"

    def __init__(self, store: DataStore):
        self.store = store

    def extract(self, x: float, y: float) -> dict:
        return self.extract_batch([(x, y)])[0]

    def extract_batch(self, pts_xy, chunk: int = 400) -> list[dict]:
        s = self.store
        out = []
        comp = s.comp_xy if s.comp_xy is not None else np.zeros((0, 2))
        for x, y in pts_xy:
            fe = _empty_features()
            if s.pop_xy is not None and len(s.pop_xy):
                d = np.hypot(s.pop_xy[:, 0] - x, s.pop_xy[:, 1] - y)
                fe["population_within_500m"] = int(s.pop_vals[d <= 500].sum())
                fe["population_within_1km"] = int(s.pop_vals[d <= 1000].sum())
                fe["population_within_1200m"] = int(s.pop_vals[d <= 1200].sum())
                fe["population_within_3km"] = int(s.pop_vals[d <= 3000].sum())
                m = d <= POP_RADIUS_M
                fe["effective_population"] = float(
                    (s.pop_vals[m] * np.exp(-d[m] / POP_DECAY_M)).sum()) if m.any() else 0.0
                fe["population_density_1km"] = round(fe["population_within_1km"] / math.pi, 1)
                fe["catchment_population_10m"] = fe["population_within_3km"]
                fe["catchment_population_20m"] = int(s.pop_vals[d <= 6000].sum())
                fe["catchment_population_30m"] = int(s.pop_vals[d <= 9000].sum())
            pt = Point(x, y)
            if s.road_geoms is not None and len(s.road_geoms):
                dany = float(np.min(shapely.distance(pt, s.road_geoms)))
                dmaj = (float(np.min(shapely.distance(pt, s.major_geoms)))
                        if len(s.major_geoms) else 9999.0)
                fe["nearest_major_road_km"] = round(dmaj / 1000.0, 3)
                fe["nearest_road_km"] = round(dany / 1000.0, 3)
                buf = pt.buffer(ROAD_DENSITY_RADIUS_M)
                length_km = float(np.sum(shapely.length(shapely.intersection(buf, s.road_geoms)))) / 1000.0
                fe["road_length_within_600m_km"] = round(length_km, 3)
                fe["road_density_km_per_km2"] = round(
                    length_km / (math.pi * (ROAD_DENSITY_RADIUS_M / 1000.0) ** 2), 2)
            if len(comp):
                dc = np.hypot(comp[:, 0] - x, comp[:, 1] - y)
                fe["competitors_within_1km"] = int((dc <= 1000).sum())
                fe["competitors_within_3km"] = int((dc <= 3000).sum())
                fe["nearest_competitor_km"] = round(float(dc.min()) / 1000.0, 3)
                order = np.argsort(dc)[:3]
                fe["nearest_competitors"] = [
                    {"name": s.comp_names[i] if i < len(s.comp_names) else "Competitor",
                     "distance_km": round(float(dc[i]) / 1000.0, 2)} for i in order]
            else:
                fe["nearest_competitor_km"] = None
                fe["nearest_competitors"] = []
            for cat, geom in s.landuse_polys:
                if geom.contains(pt):
                    fe["land_use_category"] = cat
                    break
            hits = [{"risk_type": rt, "risk_level": lvl}
                    for rt, lvl, geom in s.risk_polys if geom.contains(pt)]
            fe["risk_hits"] = hits
            rank = {"low": 0, "medium": 1, "high": 2, "critical": 3}
            fe["risk_level"] = (max(hits, key=lambda h: rank.get(h["risk_level"], 0))["risk_level"]
                                if hits else "low")
            out.append(fe)
        return out


def _empty_features() -> dict:
    return {
        "population_within_500m": 0, "population_within_1km": 0,
        "population_within_1200m": 0, "population_within_3km": 0,
        "effective_population": 0.0, "population_density_1km": 0.0,
        "catchment_population_10m": 0, "catchment_population_20m": 0,
        "catchment_population_30m": 0,
        "nearest_major_road_km": 9999.0, "nearest_road_km": 9999.0,
        "road_length_within_600m_km": 0.0, "road_density_km_per_km2": 0.0,
        "competitors_within_1km": 0, "competitors_within_3km": 0,
        "nearest_competitor_km": None, "nearest_competitors": [],
        "land_use_category": "unknown", "risk_level": "low", "risk_hits": [],
    }


# ─────────────────────────────────────────────────────────────────────────────
# ghost-rival mutation (what-if scenario) — adjusts counts/distances exactly
# like stacking the points onto the competitor table would.
# ─────────────────────────────────────────────────────────────────────────────
def apply_ghosts(fe: dict, ghost_xy: list[tuple[float, float]], x: float, y: float) -> dict:
    if not ghost_xy:
        return fe
    fe = dict(fe)
    names = list(fe.get("nearest_competitors") or [])
    for gx, gy in ghost_xy:
        d_km = math.hypot(gx - x, gy - y) / 1000.0
        if d_km <= 1.0:
            fe["competitors_within_1km"] += 1
        if d_km <= 3.0:
            fe["competitors_within_3km"] += 1
        if fe["nearest_competitor_km"] is None or d_km < fe["nearest_competitor_km"]:
            fe["nearest_competitor_km"] = round(d_km, 3)
        names.append({"name": "🧪 simulated rival", "distance_km": round(d_km, 2)})
    names.sort(key=lambda n: n["distance_km"])
    fe["nearest_competitors"] = names[:3]
    fe["simulated_extra"] = fe.get("simulated_extra", 0) + len(ghost_xy)
    return fe


# ─────────────────────────────────────────────────────────────────────────────
_EXTRACTOR = None


def init_extractor(db: GeoDB | None, store: DataStore):
    global _EXTRACTOR
    _EXTRACTOR = SQLExtractor(db) if db is not None else MemoryExtractor(store)
    print(f"✔ Feature extractor ready — mode={_EXTRACTOR.mode}")
    return _EXTRACTOR


def get_extractor():
    if _EXTRACTOR is None:
        raise RuntimeError("Feature extractor not initialised")
    return _EXTRACTOR
