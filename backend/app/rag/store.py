from __future__ import annotations

import sys
import threading

from app.config import ROOT_DIR, get_settings

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


class RAGStore:
    def __init__(self):
        self.mode: str = "pending"
        self.error: str | None = None
        self._ready = threading.Event()

    def warmup(self) -> None:
        try:
            from app.db.engine import get_geodb
            from rag import retriever
            from rag.ingest import ingest_documents
            db = get_geodb()
            if db is not None and db.table_empty("rag_chunks"):
                ingest_documents(db)
            self.mode = retriever.warm(db)
        except Exception as exc:  # noqa: BLE001
            self.mode = "lexical"
            self.error = str(exc)
            print(f"⚠ RAG warmup failed ({exc})")
        finally:
            self._ready.set()

    def warmup_background(self) -> None:
        threading.Thread(target=self.warmup, daemon=True).start()

    def retrieve(self, query: str, k: int | None = None) -> list[dict]:
        self._ready.wait(timeout=60)
        from rag import retriever
        k = k or get_settings().rag_top_k
        return retriever.retrieve(query, k=k)

    @property
    def docs(self) -> list:
        """Legacy accessor for counts/debug — returns chunk dicts."""
        self._ready.wait(timeout=60)
        from rag import retriever
        state = retriever._state
        if state.get("memory_chunks"):
            return [{"title": c["title"], "text": c.get("text", ""),
                     "tags": c.get("tags", [])} for c in state["memory_chunks"]]
        db = state.get("db")
        if db is not None:
            try:
                return db.rag_chunk_rows()
            except Exception:
                return []
        return []

    def total_docs(self) -> int:
        self._ready.wait(timeout=60)
        from rag import retriever
        return retriever.total_docs()


rag_store = RAGStore()
