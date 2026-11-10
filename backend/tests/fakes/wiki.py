from triage.adapters.types import ServiceCheck, ServiceError, WikiFacts


class FakeWiki:
    def __init__(self) -> None:
        self.by_id: dict[str, WikiFacts] = {}
        self.calls: list[str] = []
        self.down = False

    def set(self, wikidata_id: str, *types: str, extract: str | None = None) -> None:
        url = f"https://en.wikipedia.org/wiki/{wikidata_id}" if extract else None
        self.by_id[wikidata_id] = WikiFacts(types=types, extract=extract, url=url)

    async def check(self) -> ServiceCheck:
        return ServiceCheck(not self.down, "Wikidata reachable" if not self.down else "timed out")

    async def facts(self, wikidata_id: str) -> WikiFacts:
        self.calls.append(wikidata_id)
        if self.down:
            raise ServiceError("Wikidata", "timed out")
        return self.by_id.get(wikidata_id, WikiFacts())
