
from __future__ import annotations

import json
import math
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point
from shapely.ops import transform as _shp_transform
from pyproj import Transformer

UTM = "EPSG:32643"  # Rajkot → UTM zone 43N


def shp_transform_safe(func, geom):
    return _shp_transform(func, geom)

CORE_LAYERS = ["population", "roads", "competitors", "landuse", "risk"]
OPTIONAL_LAYERS = ["hospitals", "schools", "fuel"]
ALL_LAYERS = CORE_LAYERS + OPTIONAL_LAYERS

LAYER_META = {
    "population":  {"label": "Population density", "kind": "heatmap-poly", "source": "synthetic (H3 model)"},
    "roads":       {"label": "Road network",       "kind": "lines",        "source": "OpenStreetMap"},
    "competitors": {"label": "Competitors",        "kind": "points",       "source": "OSM + synthetic"},
    "landuse":     {"label": "Land use / zoning",  "kind": "polygons",     "source": "synthetic"},
    "risk":        {"label": "Environmental risk", "kind": "polygons",     "source": "synthetic"},
    "hospitals":   {"label": "Hospitals",          "kind": "points",       "source": "OpenStreetMap"},
    "schools":     {"label": "Schools",            "kind": "points",       "source": "OpenStreetMap"},
    "fuel":        {"label": "Fuel stations",      "kind": "points",       "source": "OpenStreetMap"},
}

_PROTECTED_FIRST = ["protected", "commercial", "mixed_use", "industrial", "residential", "agricultural"]


class DataStore:
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.layers: dict[str, gpd.GeoDataFrame] = {}
        self.meta: dict = {}
        self._to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
        self._to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform
        self.pop_xy: np.ndarray | None = None
        self.pop_vals: np.ndarray | None = None
        self.pop_ref: float = 1.0
        self.road_geoms: np.ndarray | None = None
        self.major_geoms: np.ndarray | None = None
        self.comp_xy: np.ndarray | None = None
        self.comp_names: list[str] = []
        self.landuse_polys: list[tuple[str, object]] = []
        self.risk_polys: list[tuple[str, str, object]] = []
        self.sites: list[dict] = []
        self.bbox = {"s": 22.22, "w": 70.70, "n": 22.38, "e": 70.92}

    def load_all(self) -> None:
        print("▶ Loading geospatial layers…")
        for name in ALL_LAYERS:
            path = self.data_dir / f"{name}.geojson"
            if not path.exists():
                print(f"  • {name}: missing, skipped")
                continue
            gdf = gpd.read_file(path)
            if gdf.crs is None:
                gdf = gdf.set_crs("EPSG:4326")
            self.layers[name] = gdf
            print(f"  ✔ {name:<12} {len(gdf):>5} features")

        meta_path = self.data_dir / "meta.json"
        if meta_path.exists():
            self.meta = json.loads(meta_path.read_text())
            self.bbox = self.meta.get("bbox", self.bbox)

        self._build_fast_arrays()
        self._load_sites()
        print(f"✔ Data store ready — population normalisation ref = {self.pop_ref:,.0f}")

    def _build_fast_arrays(self) -> None:
        pop = self.layers.get("population")
        if pop is not None and len(pop):
            pu = pop.to_crs(UTM)
            cent = pu.geometry.centroid
            self.pop_xy = np.column_stack([cent.x.values, cent.y.values])
            self.pop_vals = pop["population"].astype(float).to_numpy()
        roads = self.layers.get("roads")
        if roads is not None and len(roads):
            ru = roads.to_crs(UTM)
            geoms = ru.geometry
            self.road_geoms = geoms.to_numpy()
            majors = ru[ru["major"] == True]  # noqa: E712
            self.major_geoms = (majors.geometry.to_numpy()
                                if len(majors) else self.road_geoms)
            self.total_road_km = float(geoms.length.sum() / 1000)
        else:
            self.road_geoms = np.array([], dtype=object)
            self.major_geoms = np.array([], dtype=object)
            self.total_road_km = 0.0
        comp = self.layers.get("competitors")
        if comp is not None and len(comp):
            cu = comp.to_crs(UTM)
            self.comp_xy = np.column_stack([cu.geometry.x.values, cu.geometry.y.values])
            self.comp_names = comp.get("name", gpd.pd.Series(["Competitor"] * len(comp))).tolist()
        else:
            self.comp_xy = np.zeros((0, 2))
        lu = self.layers.get("landuse")
        if lu is not None and len(lu):
            lup = lu.to_crs(UTM)
            ordered = sorted(lup.itertuples(),
                             key=lambda r: _PROTECTED_FIRST.index(r.category)
                             if r.category in _PROTECTED_FIRST else 99)
            self.landuse_polys = [(r.category, r.geometry) for r in ordered]
        # risk
        rk = self.layers.get("risk")
        if rk is not None and len(rk):
            rkp = rk.to_crs(UTM)
            self.risk_polys = [(r.risk_type, r.risk_level, r.geometry) for r in rkp.itertuples()]

    def compute_pop_ref(self, xs: np.ndarray, ys: np.ndarray) -> None:
        if self.pop_xy is None or not len(xs):
            return
        effs = effective_population_batch(xs, ys, self.pop_xy, self.pop_vals)
        ref = float(np.percentile(effs, 95)) if len(effs) else 1.0
        if ref > 0 and math.isfinite(ref):
            self.pop_ref = round(ref * 1.08, -3)  # small headroom

    def _load_sites(self) -> None:
        preset = self.layers.get("sites") or gpd.read_file(self.data_dir / "sites.geojson")
        self.sites = []
        for row in preset.itertuples():
            self.sites.append({
                "id": row.id, "name": row.name, "preset": True,
                "latitude": row.geometry.y, "longitude": row.geometry.x,
            })
        user_path = self.data_dir / "sites_user.json"
        if user_path.exists():
            for s in json.loads(user_path.read_text()):
                s["preset"] = False
                self.sites.append(s)

    def add_site(self, name: str, lat: float, lng: float, business_type: str = "") -> dict:
        idx = sum(1 for s in self.sites if not s["preset"]) + 1
        site = {"id": f"USER_{idx:03d}", "name": name, "latitude": lat,
                "longitude": lng, "business_type": business_type, "preset": False}
        self.sites.append(site)
        self._persist_user_sites()
        return site

    def delete_site(self, site_id: str) -> bool:
        before = len(self.sites)
        self.sites = [s for s in self.sites
                      if not (s["id"] == site_id and not s["preset"])]
        changed = len(self.sites) != before
        if changed:
            self._persist_user_sites()
        return changed

    def _persist_user_sites(self) -> None:
        user = [s for s in self.sites if not s["preset"]]
        (self.data_dir / "sites_user.json").write_text(json.dumps(user, indent=2))

    def project_point(self, lat: float, lng: float) -> tuple[float, float]:
        return self._to_utm(lng, lat)

    def point_utm(self, lat: float, lng: float) -> Point:
        x, y = self.project_point(lat, lng)
        return Point(x, y)

    def polygon_utm(self, lnglat_ring: list[list[float]]):
        """[[lng, lat], ...] → shapely Polygon in UTM (closes the ring)."""
        from shapely.geometry import Polygon
        ring = [list(p) for p in lnglat_ring]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        return shp_transform_safe(self._to_utm, Polygon(ring))

    def ring_geojson(self, lat: float, lng: float, radii_m: list[int]) -> list[dict]:  # noqa: E501
        """Approximate travel-shed rings (labelled as approximations by the API)."""
        pt = self.point_utm(lat, lng)
        out = []
        for r in radii_m:
            geom_ll = gpd.GeoSeries([pt.buffer(r)], crs=UTM).to_crs("EPSG:4326").iloc[0]
            out.append({"radius_m": r, "geometry": json.loads(gpd.GeoSeries([geom_ll]).to_json())["features"][0]["geometry"]})
        return out

    def layer_catalog(self) -> list[dict]:
        cat = []
        for name in ALL_LAYERS:
            gdf = self.layers.get(name)
            if gdf is None:
                continue
            m = LAYER_META[name]
            cat.append({"name": name, "count": len(gdf), **m})
        return cat


def effective_population_batch(xs, ys, pop_xy, pop_vals, radius_m=1200, decay_km=0.6):
    """Vectorised effective-population for a batch of UTM points."""
    effs = np.zeros(len(xs))
    for i, (x, y) in enumerate(zip(xs, ys)):
        d = np.hypot(pop_xy[:, 0] - x, pop_xy[:, 1] - y)
        m = d <= radius_m
        if m.any():
            effs[i] = float((pop_vals[m] * np.exp(-(d[m] / 1000.0) / decay_km)).sum())
    return effs


store: DataStore | None = None


def get_store(data_dir: str | None = None) -> DataStore:
    global store
    if store is None:
        assert data_dir, "DataStore not initialised"
        store = DataStore(data_dir)
        store.load_all()
    return store
