"""Seed the spatial DB from the GeoJSON layers (data/*.geojson).

This is the ingest step of the real pipeline: files on disk → cleaned,
re-projected (UTM-43N, meters) → SQL inserts → GIST/HNSW indexes. Same code
seeds PostGIS (hero) and DuckDB (fallback) through the GeoDB adapter.

Run directly:      python scripts/seed_database.py
Auto-run at boot:  backend seeds DuckDB when its tables are empty
                   (PostGIS tables are seeded once and reused).
"""
from __future__ import annotations

import json

from ..geospatial.loader import UTM, DataStore
from .engine import GeoDB

# OSM-ish urban speeds (km/h) by road class — used by the routing engine.
SPEED_KMH = {
    "motorway": 60, "trunk": 50, "primary": 40, "secondary": 32,
    "tertiary": 25, "residential": 15, "service": 12, "unclassified": 15,
}


def seed_geodb(db: GeoDB, store: DataStore, drop: bool = True) -> dict:
    print(f"▶ Seeding spatial DB (mode={db.mode}, drop={drop}) …")
    db.create_schema(drop=drop)
    g = db.geom_expr()
    ph = db.ph
    counts: dict[str, int] = {}

    # ── population → centroid points ──────────────────────────────────────
    pop = store.layers.get("population")
    if pop is not None and len(pop):
        pu = pop.to_crs(UTM)
        cent = pu.geometry.centroid            # UTM centroids (geom column)
        import warnings
        with warnings.catch_warnings():        # geographic-CRS centroid warning
            warnings.simplefilter("ignore")    # is intentional: centroids IN degrees
            wcent = pop.geometry.centroid      # WGS84 centroids (lon/lat columns)
        rows = []
        for i, (h3, population, density, lon, lat, geom) in enumerate(zip(
                pop["h3"], pop["population"], pop["density"],
                wcent.x, wcent.y, cent), start=1):
            rows.append((i, str(h3), float(population), float(density),
                         float(lon), float(lat), geom.wkt))
        db.many(f"INSERT INTO population_cells (id, h3, population, density, lon, lat, geom)"
                f" VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{g})", rows)
        counts["population_cells"] = len(rows)

    # ── roads ─────────────────────────────────────────────────────────────
    roads = store.layers.get("roads")
    if roads is not None and len(roads):
        ru = roads.to_crs(UTM)
        rows = []
        for i, r in enumerate(ru.itertuples(), start=1):
            rtype = getattr(r, "road_type", "unclassified") or "unclassified"
            rows.append((i, str(rtype), str(getattr(r, "name", "Unnamed road") or "Unnamed road"),
                         bool(getattr(r, "major", False)),
                         float(SPEED_KMH.get(rtype, 15)), r.geometry.wkt))
        db.many(f"INSERT INTO roads (id, road_type, name, major, speed_kmh, geom)"
                f" VALUES ({ph},{ph},{ph},{ph},{ph},{g})", rows)
        counts["roads"] = len(rows)

    # ── competitors ───────────────────────────────────────────────────────
    comp = store.layers.get("competitors")
    if comp is not None and len(comp):
        cu = comp.to_crs(UTM)
        rows = []
        for i, r in enumerate(cu.itertuples(), start=1):
            rows.append((i, str(getattr(r, "name", "Competitor") or "Competitor"),
                         str(getattr(r, "category", "unknown") or "unknown"),
                         str(getattr(r, "source", "synthetic") or "synthetic"),
                         float(comp.iloc[i - 1].geometry.x), float(comp.iloc[i - 1].geometry.y),
                         r.geometry.wkt))
        db.many(f"INSERT INTO competitors (id, name, category, source, lon, lat, geom)"
                f" VALUES ({ph},{ph},{ph},{ph},{ph},{ph},{g})", rows)
        counts["competitors"] = len(rows)

    # ── land use ──────────────────────────────────────────────────────────
    lu = store.layers.get("landuse")
    if lu is not None and len(lu):
        lup = lu.to_crs(UTM)
        rows = [(i, str(r.category), r.geometry.wkt)
                for i, r in enumerate(lup.itertuples(), start=1)]
        db.many(f"INSERT INTO landuse (id, category, geom) VALUES ({ph},{ph},{g})", rows)
        counts["landuse"] = len(rows)

    # ── environmental risk ────────────────────────────────────────────────
    rk = store.layers.get("risk")
    if rk is not None and len(rk):
        rku = rk.to_crs(UTM)
        rows = [(i, str(getattr(r, "risk_type", "unknown")), str(getattr(r, "risk_level", "medium")),
                 r.geometry.wkt) for i, r in enumerate(rku.itertuples(), start=1)]
        db.many(f"INSERT INTO risk_zones (id, risk_type, risk_level, geom)"
                f" VALUES ({ph},{ph},{ph},{g})", rows)
        counts["risk_zones"] = len(rows)

    db.x("INSERT INTO meta_kv (key, value) VALUES ('seeded_at', ?)"
         if db.mode == "duckdb" else
         "INSERT INTO meta_kv (key, value) VALUES ('seeded_at', %s)"
         " ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
         (json.dumps({"source": "data/*.geojson"}),))
    db.commit()

    total = sum(counts.values())
    print(f"✔ Seeded {total:,} spatial rows — " +
          ", ".join(f"{k}={v:,}" for k, v in counts.items()))
    return counts
