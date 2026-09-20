import json
import math
import random
import sys
import time
from pathlib import Path

import h3
import httpx
from shapely.geometry import LineString, Point, Polygon, box, mapping
from shapely.ops import transform as shp_transform
from pyproj import Transformer

random.seed(42)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

CENTER = (22.3039, 70.8022)
BBOX = (22.22, 70.70, 22.38, 70.92)  # S, W, N, E
UTM = "EPSG:32643"  # UTM zone 43N

_to_utm = Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform
_to_ll = Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform


def to_utm_geom(geom):
    return shp_transform(_to_utm, geom)


def to_ll_geom(geom):
    return shp_transform(_to_ll, geom)


def buffer_ll(geom_ll, meters):
    """Buffer a lon/lat geometry by meters, returned in lon/lat."""
    return to_ll_geom(to_utm_geom(geom_ll).buffer(meters))


def feature(geom, props):
    return {"type": "Feature", "properties": props, "geometry": mapping(geom)}


def fc(features):
    return {"type": "FeatureCollection", "features": features}


def save(name, geojson):
    path = DATA / name
    path.write_text(json.dumps(geojson))
    n = len(geojson.get("features", []))
    print(f"  ✔ {name:<22} {n:>5} features  ({path.stat().st_size/1024:.0f} KB)")


# OpenStreetMap via Overpass
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
S, W, N, E = BBOX

QUERY = f"""
[out:json][timeout:90];
(
  way["highway"~"^(motorway|trunk|primary|secondary|tertiary)$"]({S},{W},{N},{E});
  node["amenity"~"^(hospital|clinic|school|fuel|charging_station)$"]({S},{W},{N},{E});
  way["amenity"~"^(hospital|school|university|college|charging_station)$"]({S},{W},{N},{E});
);
out geom tags;
"""


def fetch_overpass():
    print("▶ Fetching real OSM data from Overpass (Rajkot bbox)…")
    for url in [OVERPASS_URL, "https://overpass.kumi.systems/api/interpreter",
                "https://overpass.private.coffee/api/interpreter"]:
        try:
            with httpx.Client(
                    timeout=180,
                    headers={"User-Agent": "GeoReadyAI-Hackathon/1.0 (student project)"},
                    follow_redirects=True) as client:
                r = client.get(url, params={"data": QUERY})
                r.raise_for_status()
                payload = r.json()
                print(f"  ✔ Overpass responded via {url.split('/')[2]}")
                return payload
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ {url.split('/')[2]} failed ({type(exc).__name__})")
    print("  ⚠ All Overpass mirrors failed. Using synthetic road fallback.")
    return None


MAJOR = {"motorway", "trunk", "primary"}


def parse_osm(payload):
    roads, hospitals, schools, fuel, chargers = [], [], [], [], []
    seen_ids = set()

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
        elid = (el["type"], el["id"])
        if elid in seen_ids:
            continue
        seen_ids.add(elid)
        if el["type"] == "way" and "geometry" in el and "highway" in tags:
            coords = [(p["lon"], p["lat"]) for p in el["geometry"]]
            if len(coords) < 2:
                continue
            hw = tags.get("highway", "tertiary")
            roads.append(feature(LineString(coords), {
                "road_type": hw,
                "name": tags.get("name", "Unnamed road"),
                "major": hw in MAJOR,
            }))
        elif el["type"] == "node" and "amenity" in tags:
            add_poi(tags["amenity"], Point(el["lon"], el["lat"]), tags.get("name", "Unnamed"))
        elif el["type"] == "way" and "amenity" in tags and "geometry" in el:
            # building/area POIs → centroid
            lons = [p["lon"] for p in el["geometry"]]
            lats = [p["lat"] for p in el["geometry"]]
            pt = Point(sum(lons) / len(lons), sum(lats) / len(lats))
            add_poi(tags["amenity"], pt, tags.get("name", "Unnamed"))
    return roads, hospitals, schools, fuel, chargers


def synthetic_roads():
    """Fallback grid + radial road network (only used if OSM fetch fails)."""
    print("  ⚙ Building synthetic fallback road network…")
    roads = []
    cx, cy = CENTER[1], CENTER[0]
    # Ring road
    ring = buffer_ll(Point(cx, cy), 5200).exterior
    roads.append(feature(LineString(ring.coords), {"road_type": "primary", "name": "150 Feet Ring Road", "major": True}))
    # Radials
    for i, ang in enumerate(range(0, 360, 30)):
        a = math.radians(ang)
        p1 = (cx, cy)
        p2 = (cx + 0.10 * math.cos(a), cy + 0.10 * math.sin(a) / 1.08)
        roads.append(feature(LineString([p1, p2]), {"road_type": "primary" if i % 3 == 0 else "secondary", "name": f"Radial {ang}°", "major": i % 3 == 0}))
    # Grid
    for k in range(1, 5):
        d = k * 0.012
        for lon in [cx - d, cx + d]:
            roads.append(feature(LineString([(lon, cy - 0.06), (lon, cy + 0.06)]), {"road_type": "tertiary", "name": "Grid road", "major": False}))
        for lat in [cy - d, cy + d]:
            roads.append(feature(LineString([(cx - 0.06, lat), (cx + 0.06, lat)]), {"road_type": "tertiary", "name": "Grid road", "major": False}))
    return roads


# Population and synthetic layers
# Density peaks modelled on real Rajkot neighbourhoods (name, lat, lon, peak density/km², sigma km)
POP_PEAKS = [
    ("Old City core", 22.2980, 70.7925, 26000, 0.85),
    ("Sadar / Canal Rd", 22.2860, 70.7990, 17000, 0.80),
    ("Kalawad Rd corridor", 22.2910, 70.7640, 10000, 1.05),
    ("Mavdi", 22.2735, 70.7700, 11000, 1.10),
    ("University Rd", 22.2910, 70.7425, 9500, 1.20),
    ("Gandhigram / Ring Rd W", 22.3010, 70.7370, 7500, 1.35),
    ("Gondal Rd corridor", 22.2670, 70.8120, 9000, 1.05),
    ("Race Course", 22.3110, 70.7760, 8000, 1.15),
    ("Aji industrial fringe", 22.2680, 70.8310, 5500, 1.00),
]
RES9_AREA_KM2 = 0.1053


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def generate_population():
    print("▶ Generating synthetic population layer (H3 res-9 hexagons)…")
    cells = set()
    lat = S
    while lat <= N:
        lon = W
        while lon <= E:
            cells.add(h3.latlng_to_cell(lat, lon, 9))
            lon += 0.002
        lat += 0.002

    feats, total = [], 0
    for i, cell in enumerate(sorted(cells)):
        clat, clon = h3.cell_to_latlng(cell)
        d_center = haversine_km(clat, clon, *CENTER)
        base = 2600 * math.exp(-d_center / 4.2)
        density = base
        for _, plat, plon, amp, sigma in POP_PEAKS:
            d = haversine_km(clat, clon, plat, plon)
            density += amp * math.exp(-((d / sigma) ** 2))
        if d_center > 7.5:  # rural falloff
            density = min(density, 900 + 600 * random.random())
        density *= 0.88 + 0.24 * random.random()
        density *= 1.55  # scale factor → modelled total ≈ Rajkot's real urban core
        density = min(density, 32000)
        pop = int(max(0, density * RES9_AREA_KM2))
        total += pop
        boundary = [[lng, lt] for lt, lng in h3.cell_to_boundary(cell)]
        boundary.append(boundary[0])
        geom = Polygon(boundary)
        feats.append(feature(geom, {
            "h3": cell,
            "population": pop,
            "density": round(density, 0),
        }))
    print(f"  …total modelled population ≈ {total:,}")
    return feats


def generate_landuse():
    print("▶ Generating synthetic land-use zones…")
    zones = []
    # (category, (W,S,E,N))
    rects = [
        ("commercial", (70.7850, 22.2915, 70.8005, 22.3055)),   # Old City core
        ("commercial", (70.7545, 22.2845, 70.7735, 22.2990)),   # Kalawad Rd strip
        ("commercial", (70.7295, 22.2895, 70.7445, 22.3155)),   # 150ft Ring Rd W strip
        ("commercial", (70.7650, 22.2675, 70.7785, 22.2805)),   # Mavdi chowk
        ("mixed_use",  (70.7930, 22.2545, 70.8360, 22.2810)),   # Gondal Rd corridor
        ("mixed_use",  (70.7760, 22.2800, 70.7860, 22.3070)),   # West of old city
        ("industrial", (70.8190, 22.2545, 70.8460, 22.2710)),   # Aji Industrial Estate
        ("industrial", (70.7935, 22.2825, 70.8105, 22.2915)),   # Bhaktinagar industrial
        ("residential",(70.7180, 22.2835, 70.7545, 22.3310)),   # West Rajkot
        ("residential",(70.7680, 22.3110, 70.8520, 22.3620)),   # North Rajkot
        ("residential",(70.7280, 22.2385, 70.7920, 22.2675)),   # South-west Rajkot
        ("agricultural",(70.8580, 22.2200, 70.9200, 22.3010)),  # East
        ("agricultural",(70.8560, 22.3030, 70.9200, 22.3800)),  # North-east
        ("agricultural",(70.7000, 22.2200, 70.7260, 22.2800)),  # Far west
    ]
    for cat, (w, s, e, n) in rects:
        zones.append(feature(box(w, s, e, n), {"category": cat, "source": "synthetic"}))

    # Protected: Lalpari Lake + Aji riverbed corridor
    lake = buffer_ll(Point(70.7545, 22.3190), 380)
    zones.append(feature(lake, {"category": "protected", "name": "Lalpari Lake", "source": "synthetic"}))
    river = LineString([(70.70, 22.2750), (70.74, 22.2740), (70.78, 22.2820),
                        (70.82, 22.2870), (70.86, 22.2920), (70.92, 22.2970)])
    zones.append(feature(buffer_ll(river, 150), {"category": "protected", "name": "Aji riverbed", "source": "synthetic"}))
    return fc(zones), river


def generate_risk(river):
    print("▶ Generating synthetic environmental-risk layer…")
    feats = [
        feature(buffer_ll(river, 850), {"risk_type": "flood", "risk_level": "medium"}),
        feature(buffer_ll(river, 350), {"risk_type": "flood", "risk_level": "high"}),
        # one critical pocket at a river bend — perfect for the hard-constraint demo
        feature(buffer_ll(Point(70.7930, 22.2830), 260), {"risk_type": "flood", "risk_level": "critical"}),
        feature(buffer_ll(Point(70.8320, 22.2620), 1150), {"risk_type": "pollution", "risk_level": "medium"}),
    ]
    return fc(feats)


def generate_competitors(osm_chargers, landuse_fc):
    print("▶ Building competitor layer (real OSM chargers + synthetic top-up)…")
    comps = list(osm_chargers)
    # Top up to ~18 — EV chargers cluster on commercial corridors in real life
    spots = [
        ("ChargeZone — Kalawad Rd", 70.7625, 22.2900),
        ("Tata Power EZ — Ring Rd W", 70.7380, 22.3005),
        ("Statiq — Old City", 70.7945, 22.2975),
        ("Jio-bp pulse — Gondal Rd", 70.8080, 22.2660),
        ("ChargeZone — Mavdi", 70.7705, 22.2750),
        ("EV plugNgo — University Rd", 70.7445, 22.2895),
        ("Ather Grid — Sadar", 70.7985, 22.2870),
        ("Tata Power EZ — 150ft Ring Rd", 70.7355, 22.3085),
        ("Statiq — Race Course", 70.7765, 22.3105),
        ("ChargeZone — Greenland Chowkdi", 70.7685, 22.3300),
        ("Relux — Astron Chowk", 70.7655, 22.2908),
        ("Tata Power EZ — Bhaktinagar", 70.8005, 22.2865),
        ("EV plugNgo — Airport Rd", 70.7790, 22.3120),
        ("Jio-bp pulse — 80 Feet Rd", 70.7570, 22.2955),
        ("ChargeZone — Kotecha Chowk", 70.7245, 22.2895),
    ]
    for name, lon, lat in spots:
        comps.append(feature(Point(lon, lat), {
            "name": name, "category": "EV_CHARGER", "source": "synthetic",
        }))
    return fc(comps)


def preset_sites():
    print("▶ Writing preset candidate sites…")
    sites = [
        ("SITE_A", "Astron Chowk — Kalawad Rd", 22.2903, 70.7655),
        ("SITE_B", "Mavdi Chowk", 22.2741, 70.7709),
        ("SITE_C", "Gondal Road Corridor", 22.2635, 70.8060),
        ("SITE_D", "150 Feet Ring Road — West", 22.2985, 70.7385),
        ("SITE_E", "University Road", 22.2870, 70.7430),
        ("SITE_F", "Old City Core", 22.2960, 70.7930),
        ("SITE_G", "Aji Industrial Fringe", 22.2715, 70.8228),
        ("SITE_H", "Greenland Chowkdi — North", 22.3310, 70.7690),
    ]
    return fc([feature(Point(lon, lat), {"id": sid, "name": name, "preset": True})
               for sid, name, lat, lon in sites])


def main():
    t0 = time.time()
    print("═" * 60)
    print("  GeoReady-AI · Rajkot data pipeline")
    print("═" * 60)

    payload = fetch_overpass()
    roads, hospitals, schools, fuel, chargers = [], [], [], [], []
    real_ok = False
    if payload:
        roads, hospitals, schools, fuel, chargers = parse_osm(payload)
        real_ok = len(roads) >= 80
        if not real_ok:
            print("  ⚠ Too few OSM roads parsed.")

    existing_roads = DATA / "roads.geojson"
    if real_ok:
        save("roads.geojson", fc(roads))
    elif existing_roads.exists() and \
            len(json.loads(existing_roads.read_text()).get("features", [])) >= 100:
        print("  ♻ Keeping previously fetched REAL roads (fetch failed/rate-limited).")
        chargers = []  # don't disturb previously merged competitors
        hospitals = schools = fuel = []
    else:
        print("  ⚙ No previous real data — using synthetic road fallback.")
        save("roads.geojson", fc(synthetic_roads()))
    save("population.geojson", fc(generate_population()))
    landuse_fc, river = generate_landuse()
    save("landuse.geojson", landuse_fc)
    save("risk.geojson", generate_risk(river))
    if real_ok or chargers:
        save("competitors.geojson", generate_competitors(chargers, landuse_fc))
    if hospitals:
        save("hospitals.geojson", fc(hospitals))
    if schools:
        save("schools.geojson", fc(schools))
    if fuel:
        save("fuel.geojson", fc(fuel))
    save("sites.geojson", preset_sites())

    meta = {
        "area": "Rajkot Metropolitan Area, Gujarat, IN",
        "center": {"lat": CENTER[0], "lon": CENTER[1]},
        "bbox": {"s": S, "w": W, "n": N, "e": E},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "layers": {p.stem: len(json.loads(p.read_text()).get("features", []))
                   for p in sorted(DATA.glob("*.geojson"))},
        "notes": "Roads & POIs from OpenStreetMap (Overpass). Population, land-use, "
                 "risk and most competitors are synthetic, seeded from real Rajkot geography.",
    }
    (DATA / "meta.json").write_text(json.dumps(meta, indent=2))
    print(f"\n✔ Done in {time.time()-t0:.1f}s — data written to {DATA}")


if __name__ == "__main__":
    sys.exit(main())
