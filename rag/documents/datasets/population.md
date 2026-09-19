---
title: Population Dataset — Provenance & Method
tags: [data, population, dataset]
source: rag/documents/datasets/population.md
---
# Population Dataset — Provenance & Method

## What this layer is
Rajkot urban population is modelled as 4,270 H3 resolution-9 hexagonal cells,
each carrying a `population` count and `density` (persons/km²). Total modelled
population ≈ 900,000, tracking the Rajkot urban agglomeration estimate.

## How it was generated
Synthetic but geography-anchored (scripts/generate_data.py): high density in the
old-city and Race Course areas, medium along the commercial corridors
(Kalawad Road, 150ft Ring Road, Gondal Road), low at the industrial fringe and
growing west/north periphery. Generation is seeded and reproducible — the same
script always produces the same cells. This is a MODEL of demand distribution,
not census micro-data; it is labelled as synthetic everywhere the UI surfaces it.

## How the pipeline consumes it
At seed time the layer is inserted into the spatial database
(`population_cells` table, centroid points in UTM meters). Every radius query
(500 m, 1 km, 1.2 km, 3 km, catchment proxies) is a SQL aggregate over those
points. Density shown on the map reads the original polygons for rendering only —
analysis never touches the render layer.

## Replacing with real data
Point the pipeline at a census/ward GeoJSON with the same fields
(population, density, h3 or geometry) and re-run scripts/seed_database.py.
No application code changes.
