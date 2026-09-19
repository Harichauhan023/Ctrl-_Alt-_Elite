---
title: Site Readiness Scoring Methodology
tags: [scoring, methodology]
source: rag/documents/methodology/scoring.md
---
# Site Readiness Scoring Methodology

## Scoring methodology overview
GeoReady-AI computes a Site Readiness Score from 0 to 100 as a weighted sum of five normalised factors: population, accessibility, competition, land use and environmental risk. Factor weights are configurable but must sum to 100%. The score is deterministic: identical inputs and weights always produce the identical score.

## Normalisation method
Heterogeneous units (people, kilometres, counts, categories) are normalised to 0-100. Higher-is-better metrics use min-max normalisation; lower-is-better metrics such as distance to a major road use inverted exponential decay so 0 km is near 100. Population uses effective population within 1.2 km (0.6 km decay), normalised against the 95th-percentile demand of the study area.
