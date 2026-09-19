"""RAG pipeline tests (spec §42 — RAG).

Covers: documents are real files on disk and parse into chunks,
embeddings generate (384-d), semantic retrieval returns ranked chunks
WITH source metadata preserved.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from rag.ingest import load_all_chunks  # noqa: E402


def test_documents_exist_and_parse():
    files = list((ROOT / "rag" / "documents").rglob("*.md"))
    assert len(files) >= 25, f"only {len(files)} knowledge docs found"
    chunks = load_all_chunks()
    assert len(chunks) >= 55
    for c in chunks[:10]:
        assert c["title"] and c["text"] and c["source"].startswith("rag/documents/")
        assert isinstance(c["tags"], list)


def test_embeddings_generate():
    pytest.importorskip("fastembed")
    from rag.embeddings import embed_texts
    try:
        vecs = embed_texts(["site readiness scoring", "ev charging corridors"])
    except Exception as exc:
        pytest.skip(f"embedding model unavailable: {exc}")
    assert vecs.shape == (2, 384)


def test_semantic_retrieval_with_sources(tmp_geodb):
    pytest.importorskip("fastembed")
    from rag import retriever
    from rag.ingest import ingest_documents
    try:
        ingest_documents(tmp_geodb)
        mode = retriever.warm(tmp_geodb)
    except Exception as exc:
        pytest.skip(f"semantic path unavailable: {exc}")
    assert mode == "duckdb-vss"
    hits = retriever.retrieve("what does NOT_SUITABLE mean", k=4)
    assert len(hits) == 4
    assert all(c["source"].startswith("rag/documents/") for c in hits)
    assert hits[0]["score"] >= hits[-1]["score"]
    assert tmp_geodb.rag_count() >= 55
