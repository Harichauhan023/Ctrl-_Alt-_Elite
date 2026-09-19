---
title: Distance & Decay Modelling
tags: [methodology, distance]
source: rag/documents/methodology/distance.md
---
# Distance & Decay Modelling

## Distance decay rationale
Geographic influence decreases with distance: influence = e^(-distance/decay_constant). At 1 km with a 2 km constant the influence is about 0.61. Decay is applied only where analytically justified: population demand (0.6 km), major-road proximity (1.2 km) and competitor distance. Arbitrary linear cut-offs would create unrealistic cliff edges.
