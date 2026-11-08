"""Settings, connection tests, and pickers (contracts/http-api.md — Settings & connections)."""

from fastapi import APIRouter
from pydantic import BaseModel

from triage.api.deps import AdaptersDep, Owner, Settings
from triage.core.errors import TriageError
from triage.core.settings import same_folder

router = APIRouter(tags=["settings"], dependencies=[Owner])


class ServiceUnavailable(TriageError):
    status_code = 503
    code = "service_unavailable"


class RootFolderOut(BaseModel):
    path: str
    accessible: bool
    free_space: int | None
    is_intake: bool


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
