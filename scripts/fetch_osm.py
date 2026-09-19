#!/usr/bin/env python3
"""
Standalone real-OSM refresh. SAFE BY DESIGN:
  * only writes files when a full fetch succeeds with sane counts
  * on any failure it exits non-zero and changes NOTHING on disk

Use this when generate_data.py fell back to synthetic roads (e.g. Overpass
rate-limits) to restore the real OpenStreetMap layers.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_data import DATA, MAJOR, fc, feature  # noqa: E402
from generate_data import BBOX  # noqa: E402

from shapely.geometry import LineString, Point  # noqa: E402

S, W, N, E = BBOX

QUERY = f"""
[out:json][timeout:120];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({S},{W},{N},{E});
  node["amenity"~"^(hospital|clinic|school|fuel|charging_station)$"]({S},{W},{N},{E});
  way["amenity"~"^(hospital|school|university|college|charging_station)$"]({S},{W},{N},{E});
);
out geom tags;
"""

MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = {"User-Agent": "GeoReadyAI-Hackathon/1.0 (student project)"}


def parse(payload):
    roads, hospitals, schools, fuel, chargers = [], [], [], [], []
    seen = set()

    def add_poi(am, pt, name):
        if am in ("hospital", "clinic"):
            hospitals.append(feature(pt, {"name": name, "category": am}))
        elif am in ("school", "university", "college"):
            schools.append(feature(pt, {"name": name, "category": am}))
        elif am == "fuel":
            fuel.append(feature(pt, {"name": name, "category": "fuel_station"}))
        elif am == "charging_station":
            chargers.append(feature(pt, {"name": name, "category": "EV_CHARGER", "source": "osm"}))

    for el in payload.get("elements", []):
        tags = el.get("tags", {})
        key = (el["type"], el["id"])
        if key in seen:
            continue
        seen.add(key)
        if el["type"] == "way" and "geometry" in el and "highway" in tags:
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) < 2:
                continue
            hw = tags.get("highway", "tertiary")
            roads.append(feature(LineString(coords), {
                "road_type": hw, "name": tags.get("name", "Unnamed road"),
                "major": hw in MAJOR}))
        elif el["type"] == "node" and "amenity" in tags:
            add_poi(tags["amenity"], Point(el["lon"], el["lat"]), tags.get("name", "Unnamed"))
        elif el["type"] == "way" and "amenity" in tags and "geometry" in el:
            lons = [p["lon"] for p in el["geometry"]]
            lats = [p["lat"] for p in el["geometry"]]
            add_poi(tags["amenity"], Point(sum(lons)/len(lons), sum(lats)/len(lats)),
                    tags.get("name", "Unnamed"))
    return roads, hospitals, schools, fuel, chargers


def save(name, geojson):
    path = DATA / name
    path.write_text(json.dumps(geojson))
    print(f"  ✔ {name:<22} {len(geojson['features']):>5} features")


def main() -> int:
    print("═" * 56)
    print("  GeoReady-AI · standalone OSM refresh (safe mode)")
    print("═" * 56)
    payload = None
    with httpx.Client(timeout=300, headers=UA, follow_redirects=True) as client:
        for url in MIRRORS:
            host = url.split("/")[2]
            try:
                print(f"▶ Trying {host}…")
                r = client.get(url, params={"data": QUERY})
                r.raise_for_status()
                payload = r.json()
                print(f"  ✔ {host} delivered")
                break
            except Exception as exc:  # noqa: BLE001
                print(f"  ✖ {host}: {type(exc).__name__} {str(exc)[:120]}")
                time.sleep(8)
    if payload is None:
        print("\n✖ All mirrors failed — existing data files left untouched.")
        return 1

    roads, hospitals, schools, fuel, chargers = parse(payload)
    print(f"  parsed: {len(roads)} roads | {len(hospitals)} hospitals/clinics | "
          f"{len(schools)} schools/edu | {len(fuel)} fuel | {len(chargers)} real chargers")
    if len(roads) < 80:
        print("\n✖ Too few roads returned — refusing to overwrite. Untouched.")
        return 1

    save("roads.geojson", fc(roads))
    if hospitals:
        save("hospitals.geojson", fc(hospitals))
    if schools:
        save("schools.geojson", fc(schools))
    if fuel:
        save("fuel.geojson", fc(fuel))

    # merge real chargers into competitors.geojson (keep synthetic top-up)
    comp_path = DATA / "competitors.geojson"
    existing = json.loads(comp_path.read_text()) if comp_path.exists() else fc([])
    synth = [f for f in existing["features"] if f["properties"].get("source") != "osm"]
    save("competitors.geojson", fc(synth + chargers))

    # refresh meta.json layer stats
    meta_path = DATA / "meta.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
    meta["layers"] = {p.stem: len(json.loads(p.read_text()).get("features", []))
                      for p in sorted(DATA.glob("*.geojson"))}
    meta_path.write_text(json.dumps(meta, indent=2))
    print("\n✔ REAL OSM data restored. Restart the backend to reload layers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
