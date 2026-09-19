"""
Gemini multi-provider failover (PS-2 §10–§13).

  • up to 4 independently-authorised project credentials
  • temporary failures (429 / timeout / selected 5xx)  → cooldown + next provider
  • config failures (400 / 401 / 403)                  → disable provider, next
  • all providers down                                  → return None (caller falls back
    to the deterministic explainer — the app NEVER breaks on AI, PS-2 Rule 4)

Fails over provider-by-provider with exponential-backoff cooldowns; providers
automatically rejoin the rotation when their cooldown expires.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

import httpx

from ..config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"


class ProviderTemporaryError(Exception):
    pass


class ProviderConfigError(Exception):
    pass


@dataclass
class ProviderState:
    name: str
    key: str
    enabled: bool = True
    failure_count: int = 0
    cooldown_until: float = 0.0
    last_error: str | None = None

    def healthy(self) -> bool:
        return self.enabled and time.time() >= self.cooldown_until


class GeminiProviderManager:
    def __init__(self):
        s = get_settings()
        self.model = s.gemini_model
        self.timeout = s.llm_timeout_seconds
        self.max_tokens = s.llm_max_output_tokens
        self.max_attempts = s.max_llm_attempts
        self.providers: list[ProviderState] = [
            ProviderState(name=f"gemini_{i+1}", key=k)
            for i, k in enumerate([
                s.gemini_provider_1_api_key, s.gemini_provider_2_api_key,
                s.gemini_provider_3_api_key, s.gemini_provider_4_api_key,
            ]) if k
        ]
        self.call_count = 0
        self.fallback_count = 0

    @property
    def configured(self) -> int:
        return len(self.providers)

    def status(self) -> list[dict]:
        return [{
            "name": p.name, "enabled": p.enabled, "failures": p.failure_count,
            "in_cooldown": time.time() < p.cooldown_until,
            "cooldown_seconds_left": max(0, int(p.cooldown_until - time.time())),
            "last_error": p.last_error,
        } for p in self.providers]

    # ── main entry ────────────────────────────────────────────────────────
    def explain(self, system: str, user: str, expect_json: bool = True) -> tuple[dict | None, str | None]:
        """Returns (parsed_json | {"_text": ...}, provider_name) or (None, reason)."""
        if not self.providers:
            return None, "no_providers_configured"
        attempts = 0
        for p in self.providers:
            if attempts >= self.max_attempts:
                break
            if not p.healthy():
                continue
            attempts += 1
            try:
                data = self._call(p, system, user, expect_json)
                p.failure_count = 0
                self.call_count += 1
                return data, p.name
            except ProviderTemporaryError as exc:
                p.failure_count += 1
                p.last_error = str(exc)
                p.cooldown_until = time.time() + min(30 * (2 ** (p.failure_count - 1)), 600)
            except ProviderConfigError as exc:
                p.enabled = False
                p.last_error = str(exc)
                continue
            except Exception as exc:  # noqa: BLE001
                p.failure_count += 1
                p.last_error = f"unexpected: {exc}"
                p.cooldown_until = time.time() + 30
        self.fallback_count += 1
        return None, "all_providers_unavailable"

    # ── single call ───────────────────────────────────────────────────────
    def _call(self, p: ProviderState, system: str, user: str, expect_json: bool = True) -> dict:
        url = GEMINI_URL.format(model=self.model, key=p.key)
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "maxOutputTokens": self.max_tokens,
                "temperature": 0.3,
                **({"responseMimeType": "application/json"} if expect_json else {}),
            },
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(url, json=body)
        except httpx.TimeoutException as exc:
            raise ProviderTemporaryError(f"timeout after {self.timeout}s") from exc
        except httpx.HTTPError as exc:
            raise ProviderTemporaryError(f"network error: {exc}") from exc

        if r.status_code == 429:
            raise ProviderTemporaryError("429 resource exhausted / rate limited")
        if r.status_code in (400, 401, 403):
            raise ProviderConfigError(f"{r.status_code}: {r.text[:200]}")
        if r.status_code >= 500:
            raise ProviderTemporaryError(f"{r.status_code} server error")
        if r.status_code != 200:
            raise ProviderTemporaryError(f"unexpected status {r.status_code}: {r.text[:200]}")

        payload = r.json()
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderTemporaryError("malformed Gemini envelope") from exc
        return _parse_json_loose(text) if expect_json else {"_text": text.strip()}


def _parse_json_loose(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    raise ProviderTemporaryError("LLM returned non-JSON output")


provider_manager = GeminiProviderManager()
