---
title: Environmental Risk Dataset — Provenance
tags: [data, risk, flood, dataset]
source: rag/documents/datasets/environmental_risk.md
---
# Environmental Risk Dataset — Provenance

## What this layer is
Four risk polygons for the study area inside the `risk_zones` table:
two Aji-river flood pockets (risk_level high / critical), one medium flood band
along the river corridor, and one medium pollution/heat overlay in the
industrial south-east. Synthetic geometry, but anchored on the real Aji river
path and the real industrial estate location — labelled synthetic in the UI.

## How the pipeline consumes it
Point-in-polygon SQL (ST_Contains) returns every intersecting risk zone; the
engine takes the WORST level present: low=100, medium=60, high=20, critical=0
on the environment factor, and a critical pocket is also a HARD constraint
(NOT_SUITABLE overrides the numeric score).

## Replacing with real data
Any municipal flood-hazard / pollution GeoJSON can replace data/risk.geojson
(fields risk_type, risk_level ∈ low|medium|high|critical) followed by
scripts/seed_database.py. Nothing else changes.
