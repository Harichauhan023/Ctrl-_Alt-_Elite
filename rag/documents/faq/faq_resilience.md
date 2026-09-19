---
title: FAQ — Resilience & Offline Mode
tags: [faq, resilience]
source: rag/documents/faq/faq_resilience.md
---
# FAQ — Resilience & Offline Mode

## FAQ: what happens without internet
All analysis runs on local data in process memory. Without internet only two things degrade: base tiles fall back to a bundled dark style (badge shows it), and if Gemini is unreachable the deterministic explainer narrates instead. RAG embeddings are computed locally, so semantic retrieval keeps working fully offline.
