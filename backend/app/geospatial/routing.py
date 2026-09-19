"""Offline routing engine — real network-based catchments (spec §32).

Instead of public OSRM (needs internet — bad demo dependency), we are the
routing engine: the REAL OpenStreetMap road graph (1,538 ways) becomes a
networkx graph weighted by travel minutes (speed by road class), then
single-source Dijkstra gives true 10/20/30-minute isochrone polygons.

If graph construction fails for any reason we degrade to the labelled
straight-line travel-shed approximation — the endpoint never bricks.
"""
from __future__ import annotations

import json
import math

import networkx as nx
import numpy as np
import shapely

from ..db.seed import SPEED_KMH
from .loader import UTM, DataStore

MINUTES = (10, 20, 30)
FALLBACK_SPEED_KMH = 15

# straight-line fallback radius (18 km/h urban average)
FALLBACK_RADII = {10: 3000.0, 20: 6000.0, 30: 9000.0}


class RoadRouter:
    def __init__(self):
        self.graph: nx.Graph | None = None
        self.node_ids: list | None = None
        self.node_xy: np.ndarray | None = None
        self.edges = 0
        self.mode = "unavailable"

    def build(self, store: DataStore) -> None:
        roads = store.layers.get("roads")
        if roads is None or not len(roads):
            return
        print("▶ Building road routing graph (networkx Dijkstra, OSM speeds)…")
        ru = roads.to_crs(UTM)
        g = nx.Graph()
        key_to_id: dict[tuple[float, float], int] = {}
        coords: list[tuple[float, float]] = []

        def nid(x: float, y: float) -> int:
            key = (round(x * 2) / 2, round(y * 2) / 2)   # 0.5 m snap
            _id = key_to_id.get(key)
            if _id is None:
                _id = len(coords)
                key_to_id[key] = _id
                coords.append((x, y))
            return _id

        for row in ru.itertuples():
            rtype = getattr(row, "road_type", "unclassified") or "unclassified"
            speed = SPEED_KMH.get(rtype, FALLBACK_SPEED_KMH)
            m_per_min = speed * 1000.0 / 60.0
            geom = row.geometry
            parts = geom.geoms if geom.geom_type == "MultiLineString" else [geom]
            for line in parts:
                pts = list(line.coords)
                prev = None
                for x, y in pts:
                    cur = nid(x, y)
                    if prev is not None and prev != cur:
                        x0, y0 = coords[prev]
                        d = math.hypot(x - x0, y - y0)
                        g.add_edge(prev, cur, minutes=d / m_per_min)
                    prev = cur
        self.graph = g
        self.node_ids = list(range(len(coords)))
        self.node_xy = np.asarray(coords)
        self.edges = g.number_of_edges()
        self.mode = "network"
        print(f"✔ Routing graph ready — {g.number_of_nodes():,} nodes, {self.edges:,} edges")

    @property
    def ready(self) -> bool:
        return self.graph is not None and self.edges > 0

    # ─────────────────────────────────────────────────────────────────────
    def isochrones(self, store: DataStore, lat: float, lng: float,
                   extractor=None, db=None) -> dict:
        """Returns ring polygons (GeoJSON features, WGS84) + stats per minutes."""
        x, y = store.project_point(lat, lng)
        i0 = int(np.argmin(np.hypot(self.node_xy[:, 0] - x, self.node_xy[:, 1] - y)))
        lengths = nx.single_source_dijkstra_path_length(
            self.graph, self.node_ids[i0], cutoff=max(MINUTES), weight="minutes")

        rings = []
        for m in MINUTES:
            reach = np.array([self.node_xy[n] for n, t in lengths.items() if t <= m])
            if len(reach) < 12:
                # sparse pocket → honest fallback circle
                poly_utm = shapely.Point(x, y).buffer(FALLBACK_RADII[m], resolution=48)
                fallback_used = True
            else:
                mp = shapely.MultiPoint(reach)
                hull = shapely.concave_hull(mp, ratio=0.3)
                if hull.is_empty:
                    hull = mp.convex_hull
                poly_utm = hull.buffer(180)
                fallback_used = False
            pop_living, comps = _count_within(store, poly_utm, extractor, db, x, y,
                                              FALLBACK_RADII[m])
            import geopandas as gpd
            poly_ll = gpd.GeoSeries([poly_utm], crs=UTM).to_crs("EPSG:4326").iloc[0]
            rings.append({
                "minutes": m,
                "reachable_population": int(pop_living),
                "competitors_in_range": int(comps),
                "nodes_reached": int(sum(1 for t in lengths.values() if t <= m)),
                "approximate_fallback": fallback_used,
                "geometry": json.loads(gpd.GeoSeries([poly_ll]).to_json())["features"][0]["geometry"],
            })
        return rings


def _count_within(store, poly_utm, extractor, db, x, y, radius):
    """Population + competitors inside the isochrone polygon —
    SQL (ST_Within) when the DB is up, numpy/shapely otherwise."""
    if db is not None:
        try:
            sql = ("SELECT COALESCE(SUM(population),0) FROM population_cells "
                   f"WHERE ST_Within(geom, {db.geom_expr()})")
            pop = db.q(sql, (poly_utm.wkt,))[0][0]
            sql2 = ("SELECT COUNT(*) FROM competitors "
                    f"WHERE ST_Within(geom, {db.geom_expr()})")
            comps = db.q(sql2, (poly_utm.wkt,))[0][0]
            return pop or 0, comps or 0
        except Exception:
            pass  # fall through to numpy
    pop = 0
    comps = 0
    if store.pop_xy is not None and len(store.pop_xy):
        pts = shapely.points(store.pop_xy[:, 0], store.pop_xy[:, 1])
        pop = int(store.pop_vals[shapely.within(pts, poly_utm)].sum())
    if store.comp_xy is not None and len(store.comp_xy):
        pts = shapely.points(store.comp_xy[:, 0], store.comp_xy[:, 1])
        comps = int(shapely.within(pts, poly_utm).sum())
    return pop, comps


router = RoadRouter()
