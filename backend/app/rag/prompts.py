from __future__ import annotations

import json

SYSTEM_INSTRUCTION = """You are the explanation layer of GeoReady-AI, a geospatial site-readiness
analyser. Strict contract:
1. Explain ONLY the supplied factual values — never invent geographic facts.
2. NEVER change or recompute the numerical scores.
3. State strengths AND limitations honestly, incl. hard constraints if present.
4. If a metric is missing, say so instead of guessing.
5. Use concise, plain business language (no jargon dumps).
6. If a user question is provided, answer it using the same facts.
Return ONLY valid JSON with exactly these keys:
{"summary": string (2-3 sentences), "strengths": string[] (max 4),
 "risks": string[] (max 4), "key_reason": string (1 sentence)}"""


def build_user_prompt(facts: dict, rag_chunks: list[dict], question: str | None = None) -> str:
    parts = ["SITE ANALYSIS FACTS (computed by the deterministic geospatial engine):"]
    parts.append(json.dumps(facts, indent=2))
    if rag_chunks:
        parts.append("\nCONTEXT FROM KNOWLEDGE BASE (use for reasoning, not numbers):")
        for c in rag_chunks:
            parts.append(f"- [{c['title']}] {c['text']}")
    if question:
        parts.append(f"\nANALYST QUESTION: {question}")
    parts.append("\nProduce the JSON explanation now.")
    return "\n".join(parts)
