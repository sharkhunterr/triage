"""Append-only trail of every move and owner action (FR-031)."""

from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.models import AuditEvent


async def record(
    db: AsyncSession,
    *,
    actor: str,
    action: str,
    radarr_id: int | None = None,
    decision_id: int | None = None,
    from_path: str | None = None,
    to_path: str | None = None,
    result: str = "ok",
    detail: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            at=clock.now(),
            actor=actor,
            action=action,
            radarr_id=radarr_id,
            decision_id=decision_id,
            from_path=from_path,
            to_path=to_path,
            result=result,
            detail=detail,
        )
    )
    await db.flush()
