from datetime import datetime

from triage.adapters.types import SeerrRequest, ServiceCheck, ServiceError


class FakeSeerr:
    """Read-only like the real adapter: there is no write method to call."""

    def __init__(self) -> None:
        self.requests: dict[int, SeerrRequest] = {}
        self.lookups: list[int] = []
        self.sweeps = 0  # reads of every request at once
        self.down = False

    def add(
        self,
        request_id: int,
        tmdb_id: int,
        status: str = "approved",
        requested_by: str = "Alice",
        requested_at: datetime | None = None,
    ) -> None:
        self.requests[tmdb_id] = SeerrRequest(request_id, tmdb_id, status, requested_by, requested_at)

    async def check(self) -> ServiceCheck:
        return ServiceCheck(not self.down, "Seerr 2.7.0")

    async def request_for(self, tmdb_id: int) -> SeerrRequest | None:
        self.lookups.append(tmdb_id)
        if self.down:
            raise ServiceError("Seerr", "unreachable (ConnectError)")
        return self.requests.get(tmdb_id)

    async def movie_requests(self) -> dict[int, SeerrRequest]:
        self.sweeps += 1
        if self.down:
            raise ServiceError("Seerr", "unreachable (ConnectError)")
        return dict(self.requests)
