"""One-click review links (research R7): random tokens, stored hashed, single use, expiring,
revoked as soon as the movie is decided another way (Constitution VII)."""

from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from triage.core import clock
from triage.core.errors import Gone
from triage.core.security import new_token, sha256
from triage.models import ReviewLink


async def create_link(db: AsyncSession, decision_id: int, validity_days: int) -> str:
    token = new_token()
    db.add(
        ReviewLink(
            token_hash=sha256(token),
            decision_id=decision_id,
            choice="",
            expires_at=clock.now() + timedelta(days=validity_days),
        )
    )
    await db.flush()
    return token


async def usable_link(db: AsyncSession, token: str) -> ReviewLink:
    link = await db.get(ReviewLink, sha256(token))
    if link is None or link.used_at is not None or link.revoked_at is not None:
        raise Gone("This link was already used or is no longer valid", code="link_used")
    if link.expires_at <= clock.now():
        raise Gone("This link has expired", code="link_expired")
    return link


def use(link: ReviewLink, choice: str) -> None:
    link.used_at = clock.now()
    link.choice = choice
