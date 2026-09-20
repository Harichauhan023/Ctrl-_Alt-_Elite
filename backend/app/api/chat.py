
from __future__ import annotations

import json
import re

from fastapi import APIRouter

from app.ai.provider import provider_manager
from app.geospatial.hexgrid import hotspot_grid
from app.geospatial.loader import get_store
from app.rag.store import rag_store
from app.schemas.models import ChatRequest, ChatResponse
from app.scoring import engine
from app.scoring.config import BUSINESS_CONFIGS, get_business

router = APIRouter()

CHAT_SYSTEM = """You are GeoReady Assistant, a geospatial analyst copilot for the Rajkot
site-readiness platform. Rules: (1) use ONLY the structured facts provided — never invent
numbers, places or datasets; (2) answer in ≤110 words, plain business English; (3) mention
the decisive factor scores; (4) end with ONE concrete next step. No markdown headers."""

BUSINESS_KEYS = [
    (("ev", "charg"), "EV_CHARGING"),
    (("retail", "shop", "store", "kirana"), "RETAIL"),
    (("warehouse", "logistic", "fulfil", "inventory"), "WAREHOUSE"),
    (("telecom", "tower", "5g", "network"), "TELECOM_TOWER"),
    (("service center", "service centre", "workshop", "service"), "SERVICE_CENTER"),
    (("renewab", "solar", "wind"), "RENEWABLE"),
]

RECOMMEND_WORDS = ("best", "top", "recommend", "where should", "suggest", "find me",
                   "shortlist", "good area", "good zone", "ideal", "scout")
COMPARE_WORDS = ("compare", " vs ", "versus", "against", " or ")
HELP_WORDS = ("what can you", "help", "how do you work", "capabilities", "who are you")

HELP_REPLY = (
    "I'm the GeoReady Assistant — I drive the actual geospatial engine, not a canned script. Try:\n"
    "• “Recommend top zones for a warehouse” (I scan all 649 H3 zones with constraints)\n"
    "• “How is Kalawad for an EV charger?” (I run a full point analysis)\n"
    "• “Compare Old City vs Greenland for retail” (factor-by-factor table)\n"
    "• “What does NOT_SUITABLE mean?” / “explain distance decay” (knowledge + citations)\n"
    "• “What happened to the flood pocket?” (Rajkot model knowledge)\n"
    "Every number I quote came out of the deterministic engine — the citations I attach came out of the RAG store."
)


def _detect_business(msg: str) -> str | None:
    for keys, code in BUSINESS_KEYS:
        if any(k in msg for k in keys):
            return code
    return None


def _match_sites(msg: str, store) -> list[dict]:
    hits = []
    for s in store.sites:
        name_l = s["name"].lower()
        tokens = {t for t in re.split(r"[^a-z]+", name_l) if len(t) >= 4}
        if any(t in msg for t in tokens):
            hits.append(s)
    return hits


def _parse_top_k(msg: str, default: int = 5) -> int:
    m = re.search(r"(?:top|best|first)\s*(\d+)", msg) or re.search(r"(\d+)\s*(?:zones|sites|areas|cells)", msg)
    if m:
        return max(1, min(12, int(m.group(1))))
    return default


def _parse_constraints(msg: str) -> dict:
    cons: dict = {}
    m = re.search(r"no (?:more than\s*)?(\d+)\s*(?:competitor|rival)", msg)
    if m:
        cons["max_competitors_1km"] = int(m.group(1))
    if "no competitor" in msg or "zero competitor" in msg or "avoid competitor" in msg:
        cons["max_competitors_1km"] = 0
    m = re.search(r"(?:pop(?:ulation)?\s*(?:score)?\s*(?:of|at least|>=?|above)\s*)(\d+)", msg)
    if m:
        cons["min_population"] = min(100, int(m.group(1)))
    if "high population" in msg or "dense" in msg:
        cons.setdefault("min_population", 60)
    return cons


def _recommend_action(msg, business, top_k, cons):
    from app.api.recommend import recommend  # reuse the real endpoint logic
    from app.schemas.models import RecommendRequest
    req = RecommendRequest(business_type=business, top_k=top_k, **cons)
    data = recommend(req)
    label = get_business(business)["label"]
    if not data["zones"]:
        reply = (f"I scanned all {data['candidates_evaluated']} analysis zones for {label} and nothing "
                 f"survived your filters — loosen them (lower the population floor or allow a rival nearby).")
        return reply, data
    z = data["zones"]
    top = z[0]
    others = ", ".join(f"#{i+2} {x['h3'][-6:]} {x['overall']}" for i, x in enumerate(z[1:4]))
    reply = (
        f"Scanned {data['candidates_evaluated']} H3 zones for {label} — {data['surviving']} passed "
        f"(constraints: min population {cons.get('min_population', 0)}, ≤{cons.get('max_competitors_1km', 99)} "
        f"rivals within 1 km, hard-constrained cells excluded).\n"
        f"🏆 Top zone {top['h3'][-6:]}: readiness {top['overall']}/100 "
        f"(pop {top['scores']['population']:.0f}, acc {top['scores']['accessibility']:.0f}, "
        f"comp {top['scores']['competition']:.0f})."
        + (f" Next: {others}." if others else "")
        + "\nUse the fly-to chips below, then run a point analysis on your favourite."
    )
    return reply, data


def _analyze_reply(a: dict) -> str:
    d = a.get("details", {})
    m = {
        "pop": d.get("population", {}).get("population_within_1km"),
        "road": d.get("accessibility", {}).get("nearest_major_road_km"),
        "c1": d.get("competition", {}).get("competitors_within_1km"),
        "cat": d.get("land_use", {}).get("land_use_category"),
        "lvl": d.get("environment", {}).get("risk_level", "low"),
    }
    best = max(a["scores"].items(), key=lambda kv: kv[1])
    worst = min(a["scores"].items(), key=lambda kv: kv[1])
    lines = [
        f"{a.get('name') or 'That pin'} scores {a['overall_score']}/100 ({a['status'].replace('_',' ').title()}) "
        f"for {a['business_label']}.",
        f"Strongest: {best[0].replace('_',' ')} {best[1]:.0f}/100 · Weakest: {worst[0].replace('_',' ')} {worst[1]:.0f}/100.",
        f"Anchors: {m['pop']:,} people ≤1 km · major road {m['road']} km · {m['c1']} rivals ≤1 km · "
        f"land {m['cat']} · risk {m['lvl']}.",
    ]
    if a.get("constraints"):
        lines.append(f"⛔ Hard constraint active: {a['constraints'][0]}")
    return "\n".join(lines)


def _knowledge_reply(query: str, chunks: list[dict]) -> str:
    if not chunks:
        return "I don't have knowledge on that yet — try asking about scores, factors, weights, constraints, Rajkot zones or any business type."
    head = chunks[0]["text"]
    if len(chunks) > 1:
        head += "\n\n" + chunks[1]["text"]
    return head


def _llm_or_template(facts: dict, template: str, msg: str) -> tuple[str, bool, str | None]:
    if not provider_manager.configured:
        return template, False, None
    user = json.dumps(facts, default=str)
    data, pinfo = provider_manager.explain(CHAT_SYSTEM, f"USER QUESTION: {msg}\n\nFACTS:\n{user}", expect_json=False)
    if data and data.get("_text"):
        return data["_text"], True, pinfo
    return template, False, None


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    raw = req.message
    msg = f" {raw.lower()} "
    store = get_store()
    ctx_business = (req.context or {}).get("business_type")
    business = _detect_business(msg) or (ctx_business if ctx_business in BUSINESS_CONFIGS else "EV_CHARGING")
    chunks = rag_store.retrieve(raw)
    citations = [c["title"] for c in chunks]
    if any(w in msg for w in HELP_WORDS):
        return ChatResponse(reply=HELP_REPLY, action="help",
                            data={"capabilities": True}, citations=citations[:2],
                            used_llm=False, provider=None)

    sites = _match_sites(msg, store)

    if (any(w in msg for w in COMPARE_WORDS) or "compare" in msg) and len(sites) >= 2:
        results = [engine.analyze(s["latitude"], s["longitude"], business, store, None, name=s["name"])
                   for s in sites[:3]]
        winners = {}
        for f in engine.FACTORS:
            winners[f] = max(results, key=lambda r: r["scores"][f])["name"]
        winners["overall"] = max(results, key=lambda r: r["overall_score"])["name"]
        lead = next(r for r in results if r["name"] == winners["overall"])
        worst = min(results, key=lambda r: r["overall_score"])
        facts = {"task": "compare sites", "results": [
            {"name": r["name"], "overall": r["overall_score"], "status": r["status"],
             "scores": r["scores"], "constraints": r["constraints"]} for r in results]}
        template = (
            f"Comparing {' vs '.join(r['name'] for r in results)} for {get_business(business)['label']}:\n"
            + "\n".join(f"• {r['name']}: {r['overall_score']}/100 ({r['status'].replace('_',' ').title()})" for r in results)
            + f"\n🏆 {lead['name']} leads by {round(lead['overall_score']-worst['overall_score'],1)} pts."
        )
        reply, used, pinfo = _llm_or_template(facts, template, raw)
        return ChatResponse(reply=reply, action="compare",
                            data={"results": results, "winners": winners},
                            citations=citations, used_llm=used, provider=pinfo)

    if any(w in msg for w in RECOMMEND_WORDS):
        if not hotspot_grid.ready:
            return ChatResponse(reply="Zone grid is still warming up — try again in a few seconds.",
                                action="error", data=None, citations=[], used_llm=False)
        top_k = _parse_top_k(msg)
        cons = _parse_constraints(msg)
        template, data = _recommend_action(msg, business, top_k, cons)
        facts = {"task": "recommend zones", "business": business, "constraints": cons,
                 "surviving": data.get("surviving"), "top_zones": data.get("zones", [])[:top_k]}
        reply, used, pinfo = _llm_or_template(facts, template, raw)
        return ChatResponse(reply=reply, action="recommend", data=data,
                            citations=citations, used_llm=used, provider=pinfo)

    if sites:
        s = sites[0]
        a = engine.analyze(s["latitude"], s["longitude"], business, store, None, name=s["name"])
        template = _analyze_reply(a)
        facts = {"task": "explain site analysis", "analysis": engine.facts_for_llm(a)}
        reply, used, pinfo = _llm_or_template(facts, template, raw)
        return ChatResponse(reply=reply, action="analyze", data={"analysis": a},
                            citations=citations, used_llm=used, provider=pinfo)

    last = (req.context or {}).get("last_analysis")
    if last and any(w in msg for w in ("this site", "this place", "why", "it", "score", "explain")):
        template = _analyze_reply(last)
        facts = {"task": "explain current analysis", "analysis": engine.facts_for_llm(last)}
        reply, used, pinfo = _llm_or_template(facts, template, raw)
        return ChatResponse(reply=reply, action="explain_context", data={"analysis": last},
                            citations=citations, used_llm=used, provider=pinfo)

    template = _knowledge_reply(raw, chunks)
    facts = {"task": "answer knowledge question", "retrieved_chunks": chunks[:2]}
    reply, used, pinfo = _llm_or_template(facts, template, raw)
    return ChatResponse(reply=reply, action="knowledge",
                        data={"chunks": chunks,
                              "sources": [{"title": c["title"], "source": c.get("source", ""),
                                           "score": c["score"]} for c in chunks]},
                        citations=citations, used_llm=used, provider=pinfo)
