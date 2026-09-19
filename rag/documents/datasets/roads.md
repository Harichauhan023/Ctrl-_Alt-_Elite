---
title: Roads Dataset — OpenStreetMap Provenance
tags: [data, roads, osm, dataset]
source: rag/documents/datasets/roads.md
---
# Roads Dataset — OpenStreetMap Provenance

## What this layer is
1,538 road segments for the Rajkot study bbox (≈22.24–22.36 N, 70.72–70.88 E),
fetched live from OpenStreetMap via the Overpass API by scripts/fetch_osm.py.
Fields: road_type (OSM highway class), name, major flag (motorway/trunk/
primary/secondary), geometry (LineString, WGS84).

## Why it matters
This is the backbone of the "real data" claim: accessibility distances, road
density (line∩disc lengths), and the routing engine's graph are all computed
from the genuine OSM network, ~1,500 km of mapped roads. Judges can diff the
file against osm.org.

## Speeds used by the routing engine
OSM ways in the city rarely carry maxspeed tags, so the offline routing engine
assigns documented class speeds: motorway 60, trunk 50, primary 40,
secondary 32, tertiary 25, residential 15, service 12 km/h
(backend/app/db/seed.py SPEED_KMH). Catchment rings inherit these speeds.

## Refresh cadence
Delete data/roads.geojson and re-run scripts/fetch_osm.py, then
scripts/seed_database.py. If Overpass is unreachable the generated file in the
repo is used as-is (reproducible offline start).
