---
title: Glossary of Terms
tags: [glossary]
source: rag/documents/glossary/glossary.md
---
# Glossary of Terms

## Glossary: H3 hexagonal grid
H3 is Uber's hexagonal hierarchical geospatial index. GeoReady-AI uses resolution 9 (~0.1 km²) cells for the population grid and resolution 8 (~0.46 km²) cells as analysis zones for the readiness heatmap. Hexagons give uniform-neighbour geometry, unlike square grids.

## Glossary: catchment
A catchment (travel shed) is the area from which people can reach a site within a travel time budget. GeoReady-AI reports the population inside 10/20/30-minute sheds plus competitor counts, using the H3 population grid.

## Glossary: isochrone
An isochrone is the true road-network boundary reachable within a time budget, computed by routing engines such as OSRM or Valhalla. GeoReady-AI's rings approximate isochrones with constant urban speed; the /api/catchment contract is designed for a drop-in routing upgrade.

## Glossary: competition polarity
Polarity controls whether nearby rivals hurt or help. 'Avoid' (EV, warehouse, telecom, service) treats clusters as saturation. 'Attract' (retail) treats clusters as market validation. The active polarity ships inside every analysis response's details.

## Glossary: anchor metrics
Anchor metrics are the raw measurements behind each factor: population within 1 km, nearest major road (km), competitors within 1 and 3 km, nearest competitor (km), land-use category, worst risk level. Judges and analysts can trace every score to its anchors.
