#!/usr/bin/env python3
"""Retrieval quality probe (spec §40): known queries → expected source docs.

    python rag/test_retrieval.py

Prints a pass/fail table; exits non-zero if any probe misses its expected
document in the top-3.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.config import get_settings           # noqa: E402
from app.db.engine import init_geodb          # noqa: E402
from rag.ingest import ingest_documents       # noqa: E402
from rag import retriever                     # noqa: E402

PROBES = [
    ("why did my site get NOT_SUITABLE", "faq/faq_scores"),
    ("how does the competition factor handle retail vs ev", "methodology/factor_competition"),
    ("nearest major road distance decay", "methodology/factor_accessibility"),
    ("is the population data real or synthetic", "datasets/population"),
    ("what ml model do you use and how accurate", "methodology/ml_model"),
    ("h3 hexagon grid resolution 8", "glossary/glossary"),
    ("where is rajkot growing", "geography/rajkot_growth"),
    ("ev charger near highway best corridor", "business/ev_charging"),
    ("catchment travel time accuracy", "methodology/catchment"),
    ("what can the assistant do", "assistant/capabilities"),
]


def main() -> None:
    s = get_settings()
    db = init_geodb(s.database_url, s.duckdb_path)
    if not db.table_empty("rag_chunks"):
        print(f"(reusing {db.rag_count()} ingested chunks)")
    else:
        ingest_documents(db)
    mode = retriever.warm(db)
    print(f"\nretrieval mode: {mode}\n")
    fails = 0
    for q, expect in PROBES:
        hits = retriever.retrieve(q, k=3)
        sources = [h["source"] for h in hits]
        ok = any(expect in src for src in sources)
        mark = "✓" if ok else "✗"
        print(f"  {mark} {q[:52]:<54} → {hits[0]['title'][:40]:<42} {hits[0]['score']:.3f}")
        if not ok:
            print(f"      expected '{expect}' in {sources}")
            fails += 1
    print(f"\n{'ALL PROBES PASS ✅' if fails == 0 else f'{fails} probes missed ❌'}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
