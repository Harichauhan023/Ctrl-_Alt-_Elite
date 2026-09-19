---
title: FAQ — Engine & Determinism
tags: [faq, engine]
source: rag/documents/faq/faq_engine.md
---
# FAQ — Engine & Determinism

## FAQ: is the score reproducible
Yes. Every factor is a pure function of the loaded data, coordinates and weights — no randomness, no model drift. The pytest suite proves identical inputs give identical scores. AI narration sits outside the score path and can never alter it.
