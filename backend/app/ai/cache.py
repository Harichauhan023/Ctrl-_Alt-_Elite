from __future__ import annotations

import hashlib
import json
import threading
import time

CACHE_VERSION = "v1"
PROMPT_VERSION = "v1"
_TTL_SECONDS = 6 * 3600


class TTLCache:
    def __init__(self, ttl: int = _TTL_SECONDS):
        self.ttl = ttl
        self._data: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def _key(self, payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(f"{raw}|{CACHE_VERSION}|{PROMPT_VERSION}".encode()).hexdigest()

    def get(self, payload: dict) -> dict | None:
        key = self._key(payload)
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            ts, value = item
            if time.time() - ts > self.ttl:
                self._data.pop(key, None)
                return None
            return value

    def set(self, payload: dict, value: dict) -> None:
        with self._lock:
            self._data[self._key(payload)] = (time.time(), value)
            if len(self._data) > 500:  # simple bound
                oldest = sorted(self._data.items(), key=lambda kv: kv[1][0])[:100]
                for k, _ in oldest:
                    self._data.pop(k, None)


explanation_cache = TTLCache()
