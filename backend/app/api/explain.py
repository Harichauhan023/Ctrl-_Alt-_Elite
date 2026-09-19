"""AI explanation endpoint (PS-2 §38–§39, §53–§54).

Flow: structured facts → cache check → RAG top-K → Gemini failover chain →
deterministic fallback. The underlying scores are ALREADY computed; AI failure
never breaks the analysis.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..ai.cache import explanation_cache
from ..ai.explainer import deterministic_explanation
from ..ai.provider import provider_manager
from ..rag.prompts import SYSTEM_INSTRUCTION, build_user_prompt
from ..rag.store import rag_store
from ..schemas.models import ExplainRequest
from ..scoring.engine import facts_for_llm

router = APIRouter()

EXPECTED_KEYS = ("summary", "strengths", "risks", "key_reason")


@router.post("/explain")
def explain(req: ExplainRequest):
    facts = facts_for_llm(req.analysis)
    facts["question"] = req.question

    cached = explanation_cache.get(facts)
    if cached:
        return {**cached, "meta": {**cached["meta"], "cached": True}}

    business = facts.get("business_label", "business")
    query = f"{business} site readiness {facts.get('status', '')} {req.question or ''}".strip()
    chunks = rag_store.retrieve(query)
    titles = [c["title"] for c in chunks]

    explanation, meta = None, None
    if provider_manager.configured:
        data, provider_or_reason = provider_manager.explain(
            SYSTEM_INSTRUCTION, build_user_prompt(facts, chunks, req.question))
        if data is not None and isinstance(data, dict):
            explanation = {k: data.get(k) for k in EXPECTED_KEYS if data.get(k) is not None}
            for k in EXPECTED_KEYS:  # guarantee the contract shape
                explanation.setdefault(k, [] if k in ("strengths", "risks") else "")
            if req.question and data.get("answer"):
                explanation["answer"] = data["answer"]
            meta = {"used_llm": True, "provider": provider_or_reason,
                    "model": provider_manager.model, "fallback_reason": None}
        else:
            meta = {"used_llm": False, "provider": None,
                    "fallback_reason": provider_or_reason}
    else:
        meta = {"used_llm": False, "provider": None,
                "fallback_reason": "no_providers_configured"}

    if explanation is None:
        explanation = deterministic_explanation(facts, titles, req.question)

    meta.update({"rag_mode": rag_store.mode, "rag_sources": titles,
                 "sources": [{"title": c["title"], "source": c.get("source", ""),
                              "score": c["score"]} for c in chunks],
                 "pipeline": {"features": True, "ml": facts.get("ml_prediction") is not None,
                              "rag_chunks": len(chunks)}, "cached": False})
    payload = {"explanation": explanation, "meta": meta}
    explanation_cache.set(facts, payload)
    return payload
