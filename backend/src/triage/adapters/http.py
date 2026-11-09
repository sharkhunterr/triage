"""Shared HTTP plumbing: one place that turns transport and status errors into ServiceError."""

import time
from typing import Any

import httpx

from triage.adapters.types import ServiceCheck, ServiceError


def _message(response: httpx.Response) -> str | None:
    """What a service says of its refusal (``message`` in its JSON body), kept short."""
    try:
        body = response.json()
    except ValueError:
        return None
    message = body.get("message") if isinstance(body, dict) else None
    return str(message)[:200] if message else None


async def request_json(client: httpx.AsyncClient, service: str, method: str, url: str, **kwargs: Any) -> Any:
    try:
        response = await client.request(method, url, **kwargs)
    except httpx.TimeoutException as exc:
        raise ServiceError(service, "timed out") from exc
    except httpx.HTTPError as exc:
        raise ServiceError(service, f"unreachable ({exc.__class__.__name__})") from exc
    if response.status_code in (401, 403):
        raise ServiceError(service, "rejected the API key", retryable=False)
    if response.status_code == 404:
        raise ServiceError(service, "not found", retryable=False)
    if response.status_code >= 400:
        told = _message(response)
        raise ServiceError(
            service,
            f"answered HTTP {response.status_code}" + (f": {told}" if told else ""),
            retryable=response.status_code >= 500,
        )
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError as exc:
        raise ServiceError(service, "answered something that is not JSON") from exc


async def timed_check(service: str, call: Any) -> ServiceCheck:
    started = time.monotonic()
    try:
        detail = await call()
    except ServiceError as exc:
        return ServiceCheck(ok=False, detail=exc.message, latency_ms=int((time.monotonic() - started) * 1000))
    return ServiceCheck(ok=True, detail=str(detail), latency_ms=int((time.monotonic() - started) * 1000))
