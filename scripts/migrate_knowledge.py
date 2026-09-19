#!/usr/bin/env python3
"""One-off: migrate the legacy in-memory corpus (app/rag/knowledge.py) into
real markdown knowledge-base files under rag/documents/ (spec §16).

Each chunk becomes a `## Section` inside its document file; ingest.py splits
on those sections later. Front-matter carries title/tags provenance.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.rag.knowledge import KNOWLEDGE_DOCS  # noqa: E402

DOCS = ROOT / "rag" / "documents"

# id-prefix → (subfolder, filename, doc title, doc tags)
MAP = {
    "methodology_overview": ("methodology", "scoring", "Site Readiness Scoring Methodology", ["scoring", "methodology"]),
    "normalisation": ("methodology", "scoring", "Site Readiness Scoring Methodology", ["scoring", "methodology"]),
    "distance_decay": ("methodology", "distance", "Distance & Decay Modelling", ["methodology", "distance"]),
    "hard_constraints": ("methodology", "constraints", "Hard Constraints vs Soft Penalties", ["methodology", "constraints"]),
    "hotspot_method": ("methodology", "hotspots", "Hotspot Grid Methodology (H3)", ["methodology", "h3"]),
    "catchment_method": ("methodology", "catchment", "Catchment Analysis Method", ["methodology", "catchment"]),
    "ai_contract": ("methodology", "ai_contract", "Explainable-AI Contract", ["ai", "methodology"]),
    "population_factor_deep": ("methodology", "factor_population", "Population Factor Deep-Dive", ["factor", "population"]),
    "accessibility_factor_deep": ("methodology", "factor_accessibility", "Accessibility Factor Deep-Dive", ["factor", "accessibility"]),
    "competition_factor_deep": ("methodology", "factor_competition", "Competition Factor Deep-Dive", ["factor", "competition"]),
    "landuse_factor_deep": ("methodology", "factor_landuse", "Land-Use Factor Deep-Dive", ["factor", "landuse"]),
    "environment_factor_deep": ("methodology", "factor_environment", "Environment Factor Deep-Dive", ["factor", "environment"]),
    "ev_rules": ("business", "ev_charging", "EV Charging Station Business Guide", ["business", "ev"]),
    "ev_playbook": ("business", "ev_charging", "EV Charging Station Business Guide", ["business", "ev"]),
    "retail_rules": ("business", "retail", "Retail Store Business Guide", ["business", "retail"]),
    "retail_playbook": ("business", "retail", "Retail Store Business Guide", ["business", "retail"]),
    "warehouse_rules": ("business", "warehouse", "Warehouse & Fulfilment Business Guide", ["business", "warehouse"]),
    "warehouse_playbook": ("business", "warehouse", "Warehouse & Fulfilment Business Guide", ["business", "warehouse"]),
    "telecom_rules": ("business", "telecom", "Telecom Tower Business Guide", ["business", "telecom"]),
    "service_center_rules": ("business", "service_center", "Service Center Business Guide", ["business", "service"]),
    "renewable_rules": ("business", "renewable", "Renewable Energy Facility Business Guide", ["business", "renewable"]),
    "rajkot_overview": ("geography", "rajkot", "Rajkot Study Area", ["geography", "rajkot"]),
    "rajkot_corridors": ("geography", "rajkot", "Rajkot Study Area", ["geography", "rajkot"]),
    "rajkot_flood": ("geography", "rajkot_flood", "Aji River Flood Risk", ["geography", "risk", "flood"]),
    "rajkot_growth": ("geography", "rajkot_growth", "Rajkot Growth Directions", ["geography", "growth"]),
    "rajkot_data_honesty": ("geography", "rajkot_data", "Rajkot Data Provenance", ["data", "honesty"]),
    "faq_score_meaning": ("faq", "faq_scores", "FAQ — Scores & Status Bands", ["faq"]),
    "faq_not_suitable": ("faq", "faq_scores", "FAQ — Scores & Status Bands", ["faq"]),
    "faq_weights": ("faq", "faq_weights", "FAQ — Weights & Calibration", ["faq", "weights"]),
    "faq_determinism": ("faq", "faq_engine", "FAQ — Engine & Determinism", ["faq", "engine"]),
    "faq_data_synthetic": ("faq", "faq_data", "FAQ — Data & Synthesis", ["faq", "data"]),
    "faq_catchment_accuracy": ("faq", "faq_catchment", "FAQ — Catchment Accuracy", ["faq", "catchment"]),
    "faq_offline": ("faq", "faq_resilience", "FAQ — Resilience & Offline Mode", ["faq", "resilience"]),
    "faq_howto_recommend": ("faq", "faq_tools", "FAQ — Tools: Recommend & Polygon", ["faq", "tools"]),
    "faq_howto_polygon": ("faq", "faq_tools", "FAQ — Tools: Recommend & Polygon", ["faq", "tools"]),
    "glossary_h3": ("glossary", "glossary", "Glossary of Terms", ["glossary"]),
    "glossary_catchment": ("glossary", "glossary", "Glossary of Terms", ["glossary"]),
    "glossary_isochrone": ("glossary", "glossary", "Glossary of Terms", ["glossary"]),
    "glossary_polarity": ("glossary", "glossary", "Glossary of Terms", ["glossary"]),
    "glossary_anchor": ("glossary", "glossary", "Glossary of Terms", ["glossary"]),
    "scenario_market_entry": ("scenarios", "market_entry", "Playbook — Market Entry", ["scenario", "playbook"]),
    "scenario_resilience": ("scenarios", "resilience", "Playbook — Climate-Resilient Siting", ["scenario", "playbook"]),
    "scenario_cannibalisation": ("scenarios", "cannibalisation", "Playbook — Avoiding Cannibalisation", ["scenario", "playbook"]),
    "assistant_capabilities": ("assistant", "capabilities", "GeoReady Assistant Capabilities", ["assistant"]),
}


def slug_t(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def main() -> None:
    groups: dict[tuple, list[dict]] = {}
    for d in KNOWLEDGE_DOCS:
        folder, fname, doctitle, tags = MAP[d["id"]]
        key = (folder, fname, doctitle, tuple(tags))
        groups.setdefault(key, []).append(d)
    total = 0
    for (folder, fname, doctitle, tags), chunks in sorted(groups.items()):
        out = DOCS / folder / f"{fname}.md"
        out.parent.mkdir(parents=True, exist_ok=True)
        parts = ["---", f"title: {doctitle}", f"tags: [{', '.join(tags)}]",
                 f"source: rag/documents/{folder}/{fname}.md", "---", f"# {doctitle}", ""]
        for c in chunks:
            parts.append(f"## {c['title']}")
            parts.append(c["text"].strip())
            parts.append("")
            total += 1
        out.write_text("\n".join(parts))
        print(f"  ✔ {folder}/{fname}.md — {len(chunks)} sections")
    print(f"migrated {total} chunks → {DOCS}")


if __name__ == "__main__":
    main()
