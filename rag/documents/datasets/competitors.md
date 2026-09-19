---
title: Competitors Dataset — Provenance
tags: [data, competitors, dataset]
source: rag/documents/datasets/competitors.md
---
# Competitors Dataset — Provenance

## What this layer is
15 competitor points in the study area (public EV charging locations and
charging-relevant POIs), mixed provenance: real OpenStreetMap POIs
(amenity=charging_station / fuel) where mapped, plus seeded synthetic points
along real corridors where OSM coverage is sparse. Every point carries a
`source` field ("osm" or "synthetic") — the UI shows it in popups.

## How the pipeline consumes it
Points are seeded into the `competitors` table (UTM) and power the competition
factor: counts within 1 km / 3 km and nearest-competitor distance via SQL
(ST_Distance). What-if "ghost rivals" are appended onto these feature counts
client-side before scoring — the deterministic engine treats them identically.

## Growth & business meaning
The 15-point base is intentionally honest: Rajkot's public charging network is
thin, which is exactly why avoid-polarity scores are high away from the old
city. When a real national charger registry becomes available, swap the file
and re-seed — the API contract is unchanged.
