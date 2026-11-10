"""Wikidata and Wikipedia: what kind of work a movie is (Wikidata's "instance of" and "genre": concert
film, stand-up comedy, biographical film…) and the opening of its Wikipedia article, in the TMDB
language when there is one. Public APIs, no key; Wikimedia asks for a descriptive User-Agent."""

from typing import Any
from urllib.parse import quote

import httpx

from triage import __version__
from triage.adapters.http import request_json, timed_check
from triage.adapters.types import ServiceCheck, WikiFacts

SERVICE = "Wikidata"
WIKIDATA = "https://www.wikidata.org/w/api.php"
HEADERS = {
    "User-Agent": f"Triage/{__version__} (self-hosted movie sorter; https://github.com/sharkhunterr/triage)"
}
KINDS = ("P31", "P136")  # instance of, genre
GENERIC = {"Q11424"}  # "film": every movie is one, it tells nothing
EXTRACT = 600  # characters of the article's opening: enough to say what the work is


def _ids(entity: dict[str, Any]) -> list[str]:
    claims = entity.get("claims") or {}
    ids = [
        c["mainsnak"]["datavalue"]["value"]["id"]
        for prop in KINDS
        for c in claims.get(prop) or []
        if (c.get("mainsnak") or {}).get("datavalue")
    ]
    ids = [i for i in ids if i not in GENERIC]
    return list(dict.fromkeys(ids))


def _opening(text: str) -> str:
    if len(text) <= EXTRACT:
        return text
    cut = text[:EXTRACT]
    end = cut.rfind(". ")
    return cut[: end + 1] if end > EXTRACT // 2 else cut.rstrip() + "…"


class WikiClient:
    def __init__(self, client: httpx.AsyncClient | None = None, language: str = "en-US") -> None:
        self._client = client or httpx.AsyncClient(timeout=20)
        self._lang = language.split("-")[0]

    async def _get(self, url: str, params: dict[str, str] | None = None) -> Any:
        return await request_json(self._client, SERVICE, "GET", url, params=params, headers=HEADERS)

    async def check(self) -> ServiceCheck:
        async def call() -> str:
            await self._get(
                WIKIDATA, {"action": "wbgetentities", "ids": "Q11424", "props": "info", "format": "json"}
            )
            return "Wikidata reachable"

        return await timed_check(SERVICE, call)

    async def facts(self, wikidata_id: str) -> WikiFacts:
        data = await self._get(
            WIKIDATA,
            {"action": "wbgetentities", "ids": wikidata_id, "props": "claims|sitelinks", "format": "json"},
        )
        entity = ((data or {}).get("entities") or {}).get(wikidata_id) or {}
        ids = _ids(entity)
        types: list[str] = []
        if ids:
            labels = await self._get(
                WIKIDATA,
                {
                    "action": "wbgetentities",
                    "ids": "|".join(ids[:50]),
                    "props": "labels",
                    "languages": "en",
                    "format": "json",
                },
            )
            found = (labels or {}).get("entities") or {}
            types = [
                found[i]["labels"]["en"]["value"]
                for i in ids
                if ((found.get(i) or {}).get("labels") or {}).get("en")
            ]
        sitelinks = entity.get("sitelinks") or {}
        extract = url = None
        for lang in dict.fromkeys([self._lang, "en"]):
            title = (sitelinks.get(f"{lang}wiki") or {}).get("title")
            if not title:
                continue
            page = quote(title.replace(" ", "_"), safe="")
            summary = await self._get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{page}")
            text = str((summary or {}).get("extract") or "").strip()
            if text:
                extract = _opening(text)
                url = (((summary or {}).get("content_urls") or {}).get("desktop") or {}).get("page")
                break
        return WikiFacts(types=tuple(types), extract=extract, url=url)
