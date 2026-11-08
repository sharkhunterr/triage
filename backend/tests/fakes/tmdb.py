from triage.adapters.types import ServiceCheck, ServiceError, TmdbDetails


class FakeTmdb:
    def __init__(self) -> None:
        self.details_by_id: dict[int, TmdbDetails] = {}
        self.calls: list[int] = []
        self.down = False

    def set(self, tmdb_id: int, **fields: object) -> None:
        self.details_by_id[tmdb_id] = TmdbDetails(
            **{k: tuple(v) if isinstance(v, list) else v for k, v in fields.items()}  # type: ignore[arg-type]
        )

    async def check(self) -> ServiceCheck:
        return ServiceCheck(not self.down, "TMDB reachable" if not self.down else "timed out")

    async def details(self, tmdb_id: int) -> TmdbDetails:
        self.calls.append(tmdb_id)
        if self.down:
            raise ServiceError("TMDB", "timed out")
        return self.details_by_id.get(tmdb_id, TmdbDetails())
