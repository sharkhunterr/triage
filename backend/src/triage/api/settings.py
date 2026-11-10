"""Settings, connection tests, and pickers (contracts/http-api.md — Settings & connections)."""

import logging
from typing import Any, Literal

from fastapi import APIRouter, Body
from pydantic import BaseModel, ValidationError

from triage.api.deps import AdaptersDep, Db, Owner, Settings, State
from triage.core.errors import TriageError
from triage.core.security import new_token
from triage.core.settings import AppSettings, merge_update, public_view, same_folder, save_settings
from triage.worker import queue

router = APIRouter(tags=["settings"], dependencies=[Owner])
log = logging.getLogger(__name__)

Service = Literal["radarr", "tmdb", "ollama", "seerr", "smtp"]


class ServiceUnavailable(TriageError):
    status_code = 503
    code = "service_unavailable"


class InvalidSettings(TriageError):
    status_code = 422


class RootFolderOut(BaseModel):
    path: str
    accessible: bool
    free_space: int | None
    is_intake: bool


class CheckOut(BaseModel):
    ok: bool
    detail: str
    latency_ms: int


class WebhookSecret(BaseModel):
    secret: str


def _view(settings: AppSettings) -> dict[str, Any]:
    data = public_view(settings)
    base = settings.base_url or ""
    data["webhook_url"] = f"{base}/api/v1/webhooks/seerr"
    return data


def _merged(current: AppSettings, update: dict[str, Any]) -> AppSettings:
    try:
        return merge_update(current, update)
    except ValidationError as exc:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        raise InvalidSettings("Invalid settings", code="invalid", details={"errors": errors}) from exc


@router.get("/settings")
async def get_settings(settings: Settings) -> dict[str, Any]:
    return _view(settings)


@router.patch("/settings")
async def update_settings(
    db: Db, state: State, settings: Settings, update: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    merged = _merged(settings, update)
    intake = merged.radarr.intake_root_folders
    if intake and intake != settings.radarr.intake_root_folders:
        radarr = state.adapter_factory(merged).radarr
        if radarr is not None:
            folders = [f.path for f in await radarr.root_folders()]
            unknown = [p for p in intake if not any(same_folder(p, f) for f in folders)]
            if unknown:
                raise InvalidSettings(
                    "These folders are not Radarr root folders",
                    code="unknown_root_folder",
                    details={"paths": unknown},
                )
    await save_settings(db, merged)
    if merged.tmdb.api_key and merged.tmdb.language != settings.tmdb.language:
        await queue.enqueue(db, "refresh_titles", {})
    await db.commit()
    state.worker.wake()
    return _view(merged)


@router.post("/settings/test/{service}", response_model=CheckOut)
async def test_service(
    service: Service, state: State, settings: Settings, update: dict[str, Any] = Body(default_factory=dict)
) -> CheckOut:
    """Test a connection, with the values being edited when given (not saved)."""
    adapters = state.adapter_factory(_merged(settings, update))
    adapter = {
        "radarr": adapters.radarr,
        "tmdb": adapters.tmdb,
        "ollama": adapters.ollama,
        "seerr": adapters.seerr,
        "smtp": adapters.mailer,
    }[service]
    if adapter is None:
        return CheckOut(ok=False, detail="not_configured", latency_ms=0)
    try:
        check = await adapter.check()
    except Exception as exc:  # a test always answers: the page shows why it failed
        log.exception("testing %s failed", service)
        return CheckOut(ok=False, detail=f"{exc.__class__.__name__}: {exc}", latency_ms=0)
    return CheckOut(ok=check.ok, detail=check.detail, latency_ms=check.latency_ms)


@router.post("/settings/webhook-secret", response_model=WebhookSecret)
async def regenerate_webhook_secret(db: Db, settings: Settings) -> WebhookSecret:
    """A new secret for the request portal's webhook — shown this once, then write-only."""
    secret = new_token()
    settings.seerr.webhook_secret = secret
    await save_settings(db, settings)
    await db.commit()
    return WebhookSecret(secret=secret)


@router.get("/radarr/root-folders", response_model=list[RootFolderOut])
async def radarr_root_folders(settings: Settings, adapters: AdaptersDep) -> list[RootFolderOut]:
    if adapters.radarr is None:
        raise ServiceUnavailable("Connect Radarr first", code="radarr_not_configured")
    return [
        RootFolderOut(
            path=f.path,
            accessible=f.accessible,
            free_space=f.free_space,
            is_intake=any(same_folder(f.path, i) for i in settings.radarr.intake_root_folders),
        )
        for f in await adapters.radarr.root_folders()
    ]


@router.get("/ollama/models", response_model=list[str])
async def ollama_models(adapters: AdaptersDep) -> list[str]:
    if adapters.ollama is None:
        raise ServiceUnavailable("Set the Ollama address and model first", code="ollama_not_configured")
    return await adapters.ollama.models()
