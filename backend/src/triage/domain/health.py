"""Health of the connected services and of the categories' libraries (FR-022h, FR-030)."""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from triage.adapters.types import Adapters, RootFolder, ServiceCheck, ServiceError
from triage.core import clock
from triage.core.settings import same_folder
from triage.models import Category

CACHE_SECONDS = 60.0


@dataclass
class ServiceState:
    state: str  # ok | down | disabled
    detail: str
    checked_at: datetime | None


class HealthCache:
    """Probes are cached for a minute so the status page never hammers the services."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, ServiceState]] = {}

    async def check(self, adapters: Adapters) -> dict[str, ServiceState]:
        services: dict[str, Any] = {
            "radarr": adapters.radarr,
            "tmdb": adapters.tmdb,
            "ollama": adapters.ollama,
            "seerr": adapters.seerr,
            "smtp": adapters.mailer,
        }
        result: dict[str, ServiceState] = {}
        now = time.monotonic()
        for name, adapter in services.items():
            if adapter is None:
                result[name] = ServiceState("disabled", "", None)
                continue
            cached = self._entries.get(name)
            if cached is not None and now - cached[0] < CACHE_SECONDS:
                result[name] = cached[1]
                continue
            try:
                check: ServiceCheck = await adapter.check()
            except ServiceError as exc:
                check = ServiceCheck(False, exc.message)
            state = ServiceState("ok" if check.ok else "down", check.detail, clock.now())
            self._entries[name] = (now, state)
            result[name] = state
        return result

    def clear(self) -> None:
        self._entries.clear()


def folder_warnings(categories: list[Category], folders: list[RootFolder]) -> list[dict[str, str]]:
    warnings = []
    for category in categories:
        path = category.root_folder_path
        if not path:
            continue
        match = next((f for f in folders if same_folder(f.path, path)), None)
        if match is None:
            warnings.append({"category": category.name, "path": path, "problem": "missing"})
        elif not match.accessible:
            warnings.append({"category": category.name, "path": path, "problem": "inaccessible"})
    return warnings
