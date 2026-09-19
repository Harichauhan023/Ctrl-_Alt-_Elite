"""H3 readiness heatmap (PS-2 §33/§34).

Startup: extract features per H3 res-8 cell centroid with the SAME SQL
extractor used for point analysis (batched VALUES-join queries — real SQL,
amortised), then materialise the grid into the spatial DB (hotspot_cells).

A /api/hotspots request then only needs the cheap per-business mapping
(land suitability + competition polarity) and weighted sum → instant response.
"""
from __future__ import annotations

import h3
import numpy as np
from shapely.geometry import Polygon

from .loader import DataStore
from ..scoring import factors
from ..scoring.config import get_business, heatband_for
from ..scoring.engine import validate_weights

RES = 8


class HotspotGrid:
    def __init__(self):
        self.cells: list[dict] = []   # per-cell raw factor values + geometry
        self.ready = False

    # ── startup precomputation ────────────────────────────────────────────
    def build(self, store: DataStore, extractor=None, db=None) -> None:
        pop = store.layers.get("population")
        if pop is None or not len(pop) or store.pop_xy is None:
            return
        print(f"▶ Building H3 res-8 hotspot grid (features via "
              f"{extractor.mode if extractor else 'memory'} extractor)…")
        cells = sorted({h3.cell_to_parent(c, RES) for c in pop["h3"]})
        centroids = np.array([h3.cell_to_latlng(c) for c in cells])  # (lat, lng)
        pts = [store.project_point(lat, lng) for lat, lng in centroids]
        xs = np.array([p[0] for p in pts])
        ys = np.array([p[1] for p in pts])

        # population normalisation reference learned over this grid (calibration)
        store.compute_pop_ref(xs, ys)

        # real extraction — batched SQL against the spatial DB (or memory fallback)
        if extractor is not None:
            features = extractor.extract_batch(list(zip(xs.tolist(), ys.tolist())))
        else:
            from .features import MemoryExtractor
            features = MemoryExtractor(store).extract_batch(list(zip(xs.tolist(), ys.tolist())))

        self.cells = []
        db_rows = []
        for i, cell in enumerate(cells):
            lat, lng = float(centroids[i][0]), float(centroids[i][1])
            fe = features[i]

            pop_s, _ = factors.population_score(fe, store.pop_ref)
            acc_s, _ = factors.accessibility_score(fe)
            cmp_avoid, cmp_det = factors.competition_score(fe, "avoid")
            env_s, env_det = factors.environment_score(fe)
            land_cat = fe.get("land_use_category", "unknown")
            constrained = land_cat == "protected" or fe.get("risk_level") == "critical"

            boundary = [[lng_, lat_] for lat_, lng_ in h3.cell_to_boundary(cell)]
            boundary.append(boundary[0])
            raw = {
                "h3": cell, "lat": lat, "lng": lng, "boundary": boundary,
                "population": round(pop_s, 1), "accessibility": round(acc_s, 1),
                "competition_avoid": round(cmp_avoid, 1),
                "competitors_within_1km": cmp_det.get("competitors_within_1km", 0),
                "land_category": land_cat,
                "environment": round(env_s, 1),
                "risk_level": env_det.get("risk_level", "low"),
                "constrained": constrained,
            }
            self.cells.append(raw)
            if db is not None:
                ring = boundary + [boundary[0]] if boundary[0] != boundary[-1] else boundary
                poly_ll = Polygon(ring)
                import geopandas as gpd
                poly_utm = gpd.GeoSeries([poly_ll], crs="EPSG:4326").to_crs("EPSG:32643").iloc[0]
                db_rows.append({"h3": cell, "lon": lng, "lat": lat,
                                "features": raw, "wkt": poly_utm.wkt})
        if db is not None and db_rows:
            try:
                db.replace_hotspot_cells(db_rows)
                print(f"  ✔ materialised {len(db_rows)} cells → hotspot_cells table")
            except Exception as exc:
                print(f"  ⚠ hotspot materialisation skipped: {exc}")
        self.ready = True
        print(f"✔ Hotspot grid ready — {len(self.cells)} cells")

    # ── per-request rendering (fast) ──────────────────────────────────────
    def readiness_fc(self, business_type: str, weights: dict | None) -> dict:
        cfg = get_business(business_type)
        w = validate_weights(weights or cfg["weights"])
        polarity = cfg["competition_polarity"]
        feats = []
        for c in self.cells:
            comp = c["competition_avoid"] if polarity == "avoid" else max(5.0, 100 - c["competition_avoid"] * 0.8)
            land = float(cfg["landuse"].get(c["land_category"], 50))
            scores = {"population": c["population"], "accessibility": c["accessibility"],
                      "competition": round(comp, 1), "land_use": land,
                      "environment": c["environment"]}
            overall = round(sum(scores[f] * w[f] for f in scores), 1)
            band, color = heatband_for(overall)
            if c["constrained"]:
                band, color = "Restricted", "#7f1d1d"
            feats.append({
                "type": "Feature",
                "properties": {**scores, "overall": overall, "band": band, "color": color,
                               "h3": c["h3"], "constrained": c["constrained"],
                               "risk_level": c["risk_level"], "land_category": c["land_category"],
                               "competitors_within_1km": c["competitors_within_1km"]},
                "geometry": {"type": "Polygon", "coordinates": [c["boundary"]]},
            })
        return {"type": "FeatureCollection", "features": feats}

    def distribution(self, business_type: str, weights: dict | None) -> dict:
        fc = self.readiness_fc(business_type, weights)
        scores = [f["properties"]["overall"] for f in fc["features"] if not f["properties"]["constrained"]]
        bands: dict[str, int] = {}
        for f in fc["features"]:
            bands[f["properties"]["band"]] = bands.get(f["properties"]["band"], 0) + 1
        top = sorted(fc["features"], key=lambda f: -f["properties"]["overall"])[:6]
        return {
            "cells": len(scores),
            "mean": round(float(np.mean(scores)), 1) if scores else 0,
            "p90": round(float(np.percentile(scores, 90)), 1) if scores else 0,
            "bands": bands,
            "top_cells": [{"h3": t["properties"]["h3"], "overall": t["properties"]["overall"],
                           "lat": round(t["geometry"]["coordinates"][0][0][1], 4),
                           "lng": round(t["geometry"]["coordinates"][0][0][0], 4)} for t in top],
        }


hotspot_grid = HotspotGrid()


def score_cell(raw: dict, business_type: str, weights: dict | None) -> dict:
    """Score one precomputed hotspot cell for a business + weight set.
    Shared by /hotspots, /api/recommend and /api/polygon — single source of truth."""
    cfg = get_business(business_type)
    w = validate_weights(weights or cfg["weights"])
    polarity = cfg["competition_polarity"]
    comp = raw["competition_avoid"] if polarity == "avoid" else max(5.0, 100 - raw["competition_avoid"] * 0.8)
    land = float(cfg["landuse"].get(raw["land_category"], 50))
    scores = {"population": raw["population"], "accessibility": raw["accessibility"],
              "competition": round(comp, 1), "land_use": land, "environment": raw["environment"]}
    overall = round(sum(scores[f] * w[f] for f in scores), 1)
    band, color = heatband_for(overall)
    if raw["constrained"]:
        band, color = "Restricted", "#7f1d1d"
    return {**scores, "overall": overall, "band": band, "color": color,
            "constrained": raw["constrained"], "weights": w}
