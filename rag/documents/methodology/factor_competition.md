---
title: Competition Factor Deep-Dive
tags: [factor, competition]
source: rag/documents/methodology/factor_competition.md
---
# Competition Factor Deep-Dive

## Competition factor deep-dive
Competition in 'avoid' mode combines three saturating terms: 0.5*e^(-n1km/2) + 0.3*e^(-n3km/6) + 0.2*min(1, nearest_km/3). One nearby rival already halves some weight; a tight cluster saturates the market. Per-business polarity can invert the relationship (retail agglomeration mode).
