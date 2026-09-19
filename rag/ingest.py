"""RAG ingestion pipeline (spec §40).

    python rag/ingest.py

reads rag/documents/**.md → front-matter + section chunking → MiniLM
embeddings → INSERT into the vector table (rag_chunks) → HNSW index (DuckDB)
/ pgvector column (hero mode). Idempotent: replaces the corpus atomically.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "rag" / "documents"

MAX_SECTION_CHARS = 1400


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Tiny YAML-subset parser: title / tags / source between --- fences."""
    meta: dict = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    for line in text[3:end].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                v = [t.strip() for t in v[1:-1].split(",") if t.strip()]
            meta[k.strip()] = v
    return meta, text[end + 4:].strip()


def chunk_document(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(raw)
    rel = path.relative_to(ROOT).as_posix()
    doctitle = meta.get("title", path.stem.replace("_", " ").title())
    tags = meta.get("tags", [])

    # split into ## sections; anything before the first section is the intro
    parts = re.split(r"\n(?=## )", body)
    sections: list[str] = []
    for p in parts:
        p = p.strip()
        if not p or p.startswith("# ") and "\n" not in p:
            continue
        # strip the leading "# Doc title" line from the intro segment
        p = re.sub(r"^# [^\n]*\n", "", p)
        if p:
            sections.append(p)

    merged: list[str] = []
    for s in sections:
        if merged and len(s) < 120:          # fold tiny tails into the previous section
            merged[-1] += "\n\n" + s
        else:
            merged.append(s)

    chunks = []
    for i, s in enumerate(merged):
        title_match = re.match(r"^## (.+)", s)
        sec_title = title_match.group(1).strip() if title_match else doctitle
        text = re.sub(r"^## .+\n", "", s).strip()
        text = re.sub(r"\*\*", "", text)      # plain text for embedding + LLM context
        if not text:
            continue
        chunks.append({
            "document_id": f"{path.parent.name}/{path.stem}#{i}",
            "title": sec_title if sec_title != doctitle or len(merged) == 1 else doctitle,
            "text": text[:MAX_SECTION_CHARS],
            "source": rel,
            "tags": tags,
        })
    return chunks


def load_all_chunks(docs_dir: Path | None = None) -> list[dict]:
    docs_dir = docs_dir or DOCS
    files = sorted(docs_dir.rglob("*.md"))
    chunks: list[dict] = []
    for f in files:
        chunks.extend(chunk_document(f))
    return chunks


def ingest_documents(db, docs_dir: Path | None = None) -> int:
    from .embeddings import embed_texts
    chunks = load_all_chunks(docs_dir)
    texts = [f"{c['title']}. {c['text']}" for c in chunks]
    print(f"▶ Embedding {len(chunks)} chunks from {docs_dir} …")
    vecs = embed_texts(texts)
    for c, v in zip(chunks, vecs):
        c["embedding"] = v.tolist()
    db.replace_rag_chunks(chunks)
    db.create_vector_index()
    n = db.rag_count()
    print(f"✔ RAG ingested — {n} chunks → {db.mode} vector store")
    return n


def main() -> None:
    sys.path.insert(0, str(ROOT / "backend"))
    sys.path.insert(0, str(ROOT))
    from app.config import get_settings       # noqa: E402
    from app.db.engine import init_geodb      # noqa: E402
    s = get_settings()
    db = init_geodb(s.database_url, s.duckdb_path)
    ingest_documents(db)
    print("done:", db.info()["tables"]["rag_chunks"], "chunks")


if __name__ == "__main__":
    main()
