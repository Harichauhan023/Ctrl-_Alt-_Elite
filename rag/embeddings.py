"""Local embedding model — sentence-transformers/all-MiniLM-L6-v2 (spec §17).

Served through fastembed (the same HuggingFace model, quantized ONNX runtime —
no torch, no API quota, ~35 MB one-time download). 384-dimensional vectors.
"""
from __future__ import annotations

import threading

import numpy as np

_MODEL = None
_LOCK = threading.Lock()
_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def get_model():
    global _MODEL
    if _MODEL is None:
        with _LOCK:
            if _MODEL is None:
                from fastembed import TextEmbedding  # heavy import, lazy
                print(f"▶ Loading embedding model {_MODEL_NAME} (fastembed/ONNX)…")
                _MODEL = TextEmbedding(model_name=_MODEL_NAME)
    return _MODEL


def embed_texts(texts: list[str]) -> np.ndarray:
    """(n, 384) float32 — NOT normalised; cosine distance handles both."""
    m = get_model()
    return np.asarray(list(m.embed(texts)), dtype=np.float32)


def embed_query(q: str) -> list[float]:
    return embed_texts([q])[0].tolist()
