---
title: Population Factor Deep-Dive
tags: [factor, population]
source: rag/documents/methodology/factor_population.md
---
# Population Factor Deep-Dive

## Population factor deep-dive
Population is the demand proxy. Effective population = sum over H3 res-9 cells within 1.2 km of cell population times exp(-distance_km/0.6). It is normalised to the study area's 95th percentile (a saturating scale), so the densest corridors approach 100. Metrics exposed: population within 500 m, 1 km and the effective population.
