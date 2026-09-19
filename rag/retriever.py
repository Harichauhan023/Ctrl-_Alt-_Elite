"""RAG retrieval — semantic search against the vector DATABASE (spec §19).

Query → MiniLM embedding (local) → top-k by cosine similarity:
    hero     : pgvector   (embedding <=> query)
    fallback : duckdb vss (array_cosine_distance + HNSW index)
    last     : in-memory cosine over chunks freshly read from rag/documents
               (still real docs, still real embeddings — never hardcoded text)
Returns chunk dicts: {title, text, source, tags, score}.
"""
from __future__ import annotations

import re
import threading

import numpy as np

_state = {
    "ready": threading.Event(),
    "mode": "pending",          # pgvector | duckdb-vss | docs-memory | lexical | pending
    "db": None,
    "memory_chunks": None,      # [{'title', 'text', 'source', 'tags', '_vec'}]
    "embedder_ok": None,
    "error": None,
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def warm(db=None) -> str:
    """Warm the embedding model and decide the retrieval mode."""
    from . import embeddings
    _state["db"] = db
    mode = "lexical"
    try:
        embeddings.get_model()                      # raises if model can't load
        if db is not None and db.rag_count() > 0:
            # prove the SQL vector path with a live query
            probe = embeddings.embed_query("site readiness scoring")
            rows = db.vector_search(probe, k=1)
            if rows:
                mode = "pgvector" if db.mode == "postgis" else "duckdb-vss"
                print(f"✔ RAG retriever ready — {mode} "
                      f"(probe top: {rows[0]['title']} · {rows[0]['score']:.3f})")
            else:
                raise RuntimeError("vector search returned no rows")
        else:
            # docs-memory mode: real documents + real embeddings, minus SQL
            from .ingest import load_all_chunks
            chunks = load_all_chunks()
            texts = [f"{c['title']}. {c['text']}" for c in chunks]
            vecs = np.asarray(embeddings.embed_texts(texts), dtype=np.float32)
            for c, v in zip(chunks, vecs):
                c["_vec"] = v / (np.linalg.norm(v) + 1e-9)
            _state["memory_chunks"] = chunks
            mode = "docs-memory"
            print(f"✔ RAG retriever ready — docs-memory ({len(chunks)} chunks, no DB)")
        _state["embedder_ok"] = True
    except Exception as exc:  # noqa: BLE001
        # last fallback: lexical over whatever chunk text we can read
        try:
            if _state["memory_chunks"] is None and db is not None and db.rag_count() > 0:
                _state["memory_chunks"] = db.rag_chunk_rows()
            if _state["memory_chunks"] is None:
                from .ingest import load_all_chunks
                _state["memory_chunks"] = load_all_chunks()
        except Exception:
            _state["memory_chunks"] = []
        _state["error"] = str(exc)
        print(f"⚠ RAG semantic unavailable ({exc}); lexical fallback over "
              f"{len(_state['memory_chunks'])} chunks")
        _state["embedder_ok"] = False
    _state["mode"] = mode
    _state["ready"].set()
    return mode


def total_docs() -> int:
    db = _state.get("db")
    mode = _state.get("mode") or ""
    if db is not None and (mode == "pgvector" or "vss" in mode):
        try:
            return db.rag_count()
        except Exception:
            pass
    return len(_state.get("memory_chunks") or [])


def retrieve(query: str, k: int = 4) -> list[dict]:
    _state["ready"].wait(timeout=45)
    mode = _state["mode"]
    db = _state.get("db")

    if mode in ("pgvector", "duckdb-vss") and db is not None:
        from .embeddings import embed_query
        rows = db.vector_search(embed_query(query), k=k)
        return rows[:k]

    if mode == "docs-memory" and _state["memory_chunks"]:
        from .embeddings import embed_query
        q = np.asarray(embed_query(query), dtype=np.float32)
        q = q / (np.linalg.norm(q) + 1e-9)
        sims = [(i, float(c["_vec"] @ q)) for i, c in enumerate(_state["memory_chunks"])]
        sims.sort(key=lambda t: -t[1])
        out = []
        for i, s in sims[:k]:
            c = _state["memory_chunks"][i]
            out.append({"title": c["title"], "text": c["text"], "source": c.get("source", ""),
                        "tags": c.get("tags", []), "score": round(s, 4)})
        return out

    # lexical fallback
    qt = _tokens(query)
    scored = []
    for i, c in enumerate(_state.get("memory_chunks") or []):
        dt = _tokens(f"{c['title']} {c['text']} {' '.join(c.get('tags', []))}")
        union = qt | dt
        sim = len(qt & dt) / len(union) if union else 0.0
        if qt & _tokens(c["title"]):
            sim *= 1.5
        scored.append((i, sim))
    scored.sort(key=lambda t: -t[1])
    return [{"title": _state["memory_chunks"][i]["title"],
             "text": _state["memory_chunks"][i]["text"],
             "source": _state["memory_chunks"][i].get("source", ""),
             "tags": _state["memory_chunks"][i].get("tags", []),
             "score": round(s, 4)} for i, s in scored[:k]]


def mode() -> str:
    return _state["mode"]
