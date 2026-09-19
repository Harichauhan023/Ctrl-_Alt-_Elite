---
title: FAQ — Tools: Recommend & Polygon
tags: [faq, tools]
source: rag/documents/faq/faq_tools.md
---
# FAQ — Tools: Recommend & Polygon

## FAQ: how the site recommender works
The recommender searches the precomputed H3 zone grid: it applies your business type and weights, filters by constraints (minimum population score, maximum nearby competitors, exclude hard-constrained cells), then ranks survivors by overall readiness and returns the top-K with coordinates you can fly to and analyse one by one.

## FAQ: how polygon area analysis works
Draw a polygon on the map. The engine aggregates inside it: total modelled population (res-9 centroids), road kilometres (true line intersection), competitor counts, land-use mix, risk mix, and the distribution of H3 zone readiness. It answers 'how healthy is this whole district' rather than a single parcel.
