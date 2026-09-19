---
title: Environment Factor Deep-Dive
tags: [factor, environment]
source: rag/documents/methodology/factor_environment.md
---
# Environment Factor Deep-Dive

## Environment factor deep-dive
Risk polygons carry a type (flood, pollution) and level mapped low=100, medium=60, high=20, critical=0. Where polygons overlap a point, the WORST level governs — one critical pocket overrides every mild band. Critical levels are simultaneously a hard constraint marking the site NOT_SUITABLE.
