"""Ollama: the local AI, asked only for ambiguous movies, constrained to a JSON answer."""

import json
import time
from typing import Any

import httpx

from triage.adapters.http import request_json, timed_check
from triage.adapters.types import AiVerdict, ServiceCheck, ServiceError

SERVICE = "Ollama"
UNSURE = "unsure"


def answer_schema(category_keys: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": [*category_keys, UNSURE]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "reasoning": {"type": "string", "maxLength": 600},
        },
        "required": ["category", "confidence", "reasoning"],
    }


def parse_verdict(content: str, category_keys: list[str], duration_ms: int = 0) -> AiVerdict:
    """Validate the model's answer; anything off-schema is an error, never a guess."""
    try:
        data = json.loads(content)
    except ValueError as exc:
        raise ServiceError(SERVICE, "answered something that is not JSON", retryable=False) from exc
    if not isinstance(data, dict):
        raise ServiceError(SERVICE, "answered an unexpected shape", retryable=False)
    category = data.get("category")
    if category not in [*category_keys, UNSURE]:
        raise ServiceError(SERVICE, f"chose an unknown category: {category!r}", retryable=False)
    try:
        confidence = min(1.0, max(0.0, float(data.get("confidence", 0))))
    except (TypeError, ValueError) as exc:
        raise ServiceError(SERVICE, "gave no usable confidence", retryable=False) from exc
    reasoning = str(data.get("reasoning") or "")[:600]
    return AiVerdict(category=category, confidence=confidence, reasoning=reasoning, duration_ms=duration_ms)


class OllamaClient:
    def __init__(self, url: str, model: str, timeout_s: int, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient()
        self._base = url.rstrip("/")
        self._model = model
        self._timeout = timeout_s

    async def check(self) -> ServiceCheck:
        async def call() -> str:
            models = await self.models()
            if self._model and self._model not in models:
                raise ServiceError(SERVICE, f"model {self._model} is not installed", retryable=False)
            return f"{len(models)} models"

        return await timed_check(SERVICE, call)

    async def models(self) -> list[str]:
        data = await request_json(self._client, SERVICE, "GET", f"{self._base}/api/tags", timeout=15)
        return sorted(m["name"] for m in (data or {}).get("models") or [] if m.get("name"))

    async def classify(self, system: str, user: str, category_keys: list[str]) -> AiVerdict:
        started = time.monotonic()
        data = await request_json(
            self._client,
            SERVICE,
            "POST",
            f"{self._base}/api/chat",
            timeout=self._timeout,
            json={
                "model": self._model,
                "stream": False,
                "format": answer_schema(category_keys),
                "options": {"temperature": 0},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        )
        content = ((data or {}).get("message") or {}).get("content") or ""
        return parse_verdict(content, category_keys, int((time.monotonic() - started) * 1000))
