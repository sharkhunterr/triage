"""Ollama: the local AI, asked only for ambiguous movies, constrained to a JSON answer."""

import json
import time
from typing import Any

import httpx

from triage.adapters.http import request_json, timed_check
from triage.adapters.types import AiVerdict, ServiceCheck, ServiceError

SERVICE = "Ollama"
UNSURE = "unsure"
# the reasoning's length is the owner's call (their instructions); the cap only guards a runaway
REASONING_MAX = 2000
SENTENCE_ENDS = (".", "!", "?", "…")

# The answer is a short JSON object, so generation is capped and the context is fixed: each call
# stays brief, and a fixed context never forces the model to reload (which would spike the GPU).
NUM_CTX = 8192
NUM_PREDICT = 1024
# The reasoning counts in the cap: with thinking on, it leaves room for it before the verdict.
NUM_PREDICT_THINKING = 4096
# Kept loaded between the movies of a batch: on a CPU, reloading a model takes tens of seconds.
KEEP_ALIVE = "30m"


def think_mode(model: str, thinking: bool = False) -> bool | str:
    """A reasoning pass before the verdict only when the owner asks for it. gpt-oss takes a
    reasoning level, not a boolean: with ``False`` it answers an empty message, so it gets the
    lowest level instead, and its medium one when thinking is on."""
    if model.startswith("gpt-oss"):
        return "medium" if thinking else "low"
    return thinking


def answer_schema(category_keys: list[str]) -> dict[str, Any]:
    """The model writes the fields in this order, so the reasoning comes first: asked for the
    category first, it commits before any reasoning (leaning on the first category), then writes a
    reasoning that contradicts its own choice."""
    return {
        "type": "object",
        "properties": {
            "reasoning": {"type": "string", "maxLength": REASONING_MAX},
            "category": {"type": "string", "enum": [*category_keys, UNSURE]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": ["reasoning", "category", "confidence"],
    }


def whole_sentences(reasoning: str) -> str:
    """The schema caps the reasoning, so a long one is cut mid-word: it ends on its last whole
    sentence instead, or with an ellipsis when it has none."""
    text = reasoning.strip()
    if len(reasoning) < REASONING_MAX or text.endswith(SENTENCE_ENDS):
        return text
    end = max(text.rfind(f"{mark} ") for mark in SENTENCE_ENDS)
    return text[: end + 1] if end > 0 else text.rstrip(" ,;:") + "…"


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
    reasoning = whole_sentences(str(data.get("reasoning") or "")[:REASONING_MAX])
    return AiVerdict(category=category, confidence=confidence, reasoning=reasoning, duration_ms=duration_ms)


class OllamaClient:
    def __init__(
        self,
        url: str,
        model: str,
        timeout_s: int,
        client: httpx.AsyncClient | None = None,
        *,
        thinking: bool = False,
    ) -> None:
        self._client = client or httpx.AsyncClient()
        self._base = url.rstrip("/")
        self._model = model
        self._timeout = timeout_s
        self._thinking = thinking

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
                "keep_alive": KEEP_ALIVE,
                # thinking models (qwen3…) otherwise generate a long reasoning pass before the JSON,
                # which holds the GPU far longer than the verdict needs: only when the owner asks
                "think": think_mode(self._model, self._thinking),
                "format": answer_schema(category_keys),
                "options": {
                    "temperature": 0,
                    "num_ctx": NUM_CTX,
                    "num_predict": NUM_PREDICT_THINKING if self._thinking else NUM_PREDICT,
                },
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        )
        content = ((data or {}).get("message") or {}).get("content") or ""
        return parse_verdict(content, category_keys, int((time.monotonic() - started) * 1000))
