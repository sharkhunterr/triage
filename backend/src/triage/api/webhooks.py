"""Seerr (Overseerr / Jellyseerr) webhook: an approved movie request triggers an immediate poll.

Protected by the shared secret the portal sends in its "Authorization Header" field.
"""

import hmac
from typing import Any

from fastapi import APIRouter, Body, Header, Response

from triage.api.deps import Settings, State
from triage.core.errors import Unauthorized

router = APIRouter(tags=["webhooks"])

APPROVED = {"MEDIA_APPROVED", "MEDIA_AUTO_APPROVED"}
FOLLOW_UPS = (10.0, 30.0, 90.0)


@router.post("/webhooks/seerr", status_code=202)
async def seerr_webhook(
    settings: Settings,
    state: State,
    payload: dict[str, Any] = Body(default_factory=dict),
    authorization: str = Header(default=""),
) -> Response:
    expected = settings.seerr.webhook_secret
    if not expected or not hmac.compare_digest(authorization.encode(), expected.encode()):
        raise Unauthorized("Wrong or missing webhook secret", code="bad_webhook_secret")
    media = payload.get("media") or {}
    if payload.get("notification_type") in APPROVED and media.get("media_type") == "movie":
        # Seerr notifies before Radarr has added the movie: check now, then again shortly after.
        state.worker.wake(follow_up_s=FOLLOW_UPS)
        return Response(status_code=202)
    return Response(status_code=204)
