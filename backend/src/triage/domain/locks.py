"""Locks: the library the owner chose by hand for a movie. A check that respects locks leaves a
locked movie where it is; a bulk application of proposals never locks."""

from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.core.settings import normalize_folder, same_folder
from triage.models import Decision, MovieRef

SHEET = "sheet"  # a button on the movie's sheet
REVIEW = "review"  # the review queue
EMAIL = "email"  # a one-click link of the review email
CHECK_GAP = "check_gap"  # a gap a check found
CHECK_DOUBT = "check_doubt"  # a doubt a check left
VIAS = {SHEET, REVIEW, EMAIL, CHECK_GAP, CHECK_DOUBT}


def via_of(decision: Decision) -> str:
    """Where a choice on this decision is made, when the caller does not say."""
    if decision.scan_id is not None:
        return CHECK_GAP if decision.status == "proposed" else CHECK_DOUBT
    return REVIEW


async def lock(db: AsyncSession, radarr_id: int, folder: str | None, via: str) -> None:
    ref = await db.get(MovieRef, radarr_id)
    if ref is None or not folder:
        return
    ref.locked_folder = normalize_folder(folder)
    ref.locked_via = via
    ref.locked_at = clock.now()


async def unlock(db: AsyncSession, radarr_id: int) -> None:
    ref = await db.get(MovieRef, radarr_id)
    if ref is not None:
        ref.locked_folder = ref.locked_via = ref.locked_at = None


def holds(ref: MovieRef | None, folder: str | None) -> bool:
    """Whether the movie is locked in this folder. A lock on another folder (a move still on its
    way, or the movie moved since by hand in Radarr) holds nothing."""
    return bool(ref and ref.locked_folder and same_folder(ref.locked_folder, folder))
