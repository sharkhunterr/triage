"""Real adapters against recorded payloads (contracts/external-services.md)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest

from triage.adapters.ollama import OllamaClient, parse_verdict
from triage.adapters.radarr import RadarrClient
from triage.adapters.seerr import SeerrClient
from triage.adapters.tmdb import RateLimiter, TmdbClient
from triage.adapters.types import ServiceError

PAYLOADS = Path(__file__).parent / "payloads"


def payload(name: str) -> Any:
    return json.loads((PAYLOADS / name).read_text())


class Recorder:
    def __init__(self, routes: dict[tuple[str, str], Any]) -> None:
        self.routes = routes
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = self.routes.get((request.method, request.url.path))
        if body is None:
            return httpx.Response(404)
        if isinstance(body, httpx.Response):
            return body
        return httpx.Response(200, json=body)

    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self))


async def test_radarr_reads_movies_and_root_folders():
    rec = Recorder(
        {
            ("GET", "/api/v3/movie"): [payload("radarr_movie.json")],
            ("GET", "/api/v3/rootfolder"): payload("radarr_rootfolder.json"),
        }
    )
    radarr = RadarrClient("http://radarr:7878/", "key", rec.client())
    (movie,) = await radarr.movies()
    assert (movie.id, movie.tmdb_id, movie.root_folder_path) == (12, 862, "/data/media/nouveaux")
    assert movie.genres[0] == "Animation" and movie.studio == "Pixar"
    assert movie.original_language == "English" and movie.certification == "G"
    assert movie.poster_url and movie.poster_url.startswith("https://image.tmdb.org")
    assert movie.added == datetime(2026, 11, 8, 9, 30, tzinfo=UTC)  # when Radarr added it
    folders = await radarr.root_folders()
    assert [f.accessible for f in folders] == [True, True, False]
    assert all(r.headers["X-Api-Key"] == "key" for r in rec.requests)


async def test_radarr_move_uses_the_editor_and_never_deletes():
    rec = Recorder({("PUT", "/api/v3/movie/editor"): httpx.Response(202, json=[])})
    await RadarrClient("http://radarr:7878", "key", rec.client()).move(12, "/data/media/dessin-anime")
    (request,) = rec.requests
    assert json.loads(request.content) == {
        "movieIds": [12],
        "rootFolderPath": "/data/media/dessin-anime",
        "moveFiles": True,
        "deleteFiles": False,
        "addImportExclusion": False,
    }


async def test_radarr_bad_key_is_not_retryable():
    rec = Recorder({("GET", "/api/v3/movie"): httpx.Response(401)})
    with pytest.raises(ServiceError) as caught:
        await RadarrClient("http://radarr:7878", "bad", rec.client()).movies()
    assert not caught.value.retryable


async def test_radarr_unknown_movie_is_none():
    rec = Recorder({})
    assert await RadarrClient("http://radarr:7878", "key", rec.client()).movie(999) is None


async def test_tmdb_details_with_keywords_and_certifications():
    rec = Recorder({("GET", "/3/movie/862"): payload("tmdb_movie.json")})
    details = await TmdbClient("v3key", rec.client(), RateLimiter(1000)).details(862)
    assert details.genres == ("Animation", "Adventure", "Family", "Comedy")
    assert "computer animation" in details.keywords
    assert details.companies == ("Pixar",)
    assert details.certifications == ("G",)  # the country of the TMDB language (en-US by default)
    (request,) = rec.requests
    assert request.url.params["append_to_response"] == "keywords,release_dates,translations,images"
    assert request.url.params["include_image_language"] == "en,null"
    assert request.url.params["api_key"] == "v3key"
    # stills without text first, the best voted first among them
    assert details.images == ("/plain-top.jpg", "/plain-low.jpg", "/en-text.jpg", "/fr-text.jpg")


async def test_tmdb_in_french_gives_the_french_rating_and_synopsis():
    rec = Recorder({("GET", "/3/movie/862"): payload("tmdb_movie.json")})
    details = await TmdbClient("v3key", rec.client(), RateLimiter(1000), language="fr-FR").details(862)
    assert details.certifications == ("U",)
    assert details.overview == "Woody, le jouet préféré d'Andy, voit arriver Buzz l'Éclair."
    assert details.title == "Toy Story : les jouets"
    assert details.genres[0] == "Animation"  # genres stay in English, the language rules are written in
    assert rec.requests[0].url.params["include_image_language"] == "fr,en,null"


async def test_tmdb_without_a_rating_for_the_country_falls_back_to_the_us_one():
    rec = Recorder({("GET", "/3/movie/862"): payload("tmdb_movie.json")})
    details = await TmdbClient("v3key", rec.client(), RateLimiter(1000), language="de-DE").details(862)
    assert details.certifications == ("G",)
    assert details.overview == "Led by Woody, Andy's toys live happily in his room..."


async def test_tmdb_keeps_the_original_title_when_the_country_has_no_title_of_its_own():
    """fr-FR exists with an empty title (French title = original): never take Quebec's instead."""
    data = payload("tmdb_movie.json")
    for t in data["translations"]["translations"]:
        if t["iso_3166_1"] == "FR":
            t["data"]["title"] = ""
        if t["iso_3166_1"] == "CA":
            t["data"]["title"] = "Histoire de jouets"
    rec = Recorder({("GET", "/3/movie/862"): data})
    details = await TmdbClient("v3key", rec.client(), RateLimiter(1000), language="fr-FR").details(862)
    assert details.title is None  # Radarr's title stays
    assert details.overview == "Woody, le jouet préféré d'Andy, voit arriver Buzz l'Éclair."


async def test_tmdb_read_token_goes_in_the_header():
    rec = Recorder({("GET", "/3/configuration"): {}})
    check = await TmdbClient("aaa.bbb.ccc", rec.client(), RateLimiter(1000)).check()
    assert check.ok
    assert rec.requests[0].headers["Authorization"] == "Bearer aaa.bbb.ccc"


async def test_ollama_chat_is_constrained_to_the_categories():
    rec = Recorder({("POST", "/api/chat"): payload("ollama_chat.json")})
    verdict = await OllamaClient("http://ollama:11434", "qwen3:8b", 60, rec.client()).classify(
        "system", "user", ["animation", "films"]
    )
    assert (verdict.category, verdict.confidence) == ("animation", 0.92)
    body = json.loads(rec.requests[0].content)
    assert body["stream"] is False and body["options"] == {"temperature": 0}
    assert body["format"]["properties"]["category"]["enum"] == ["animation", "films", "unsure"]


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[1, 2]",
        '{"category": "documentary", "confidence": 1, "reasoning": "x"}',
        '{"category": "films", "confidence": "high", "reasoning": "x"}',
    ],
)
def test_ollama_answers_off_schema_are_errors(content: str):
    with pytest.raises(ServiceError):
        parse_verdict(content, ["animation", "films"])


async def test_seerr_asks_only_what_every_seerr_knows_and_skips_series():
    """Overseerr 1.35 refuses a query parameter it does not know (`mediaType`, a Jellyseerr one) with
    HTTP 400: the requests are asked without it, and a series sharing the movie's TMDB id is skipped."""
    known = {"take", "skip", "filter", "sort", "requestedBy"}
    series = {"id": 50, "status": 2, "type": "tv", "media": {"id": 9, "tmdbId": 862, "mediaType": "tv"}}
    body = payload("seerr_requests.json")
    body["results"].insert(0, series)

    def overseerr(request: httpx.Request) -> httpx.Response:
        unknown = set(request.url.params) - known
        if unknown:
            message = f"Unknown query parameter '{sorted(unknown)[0]}'"
            return httpx.Response(400, json={"message": message, "errors": [{"message": message}]})
        return httpx.Response(200, json=body)

    seerr = SeerrClient(
        "http://seerr:5055", "key", httpx.AsyncClient(transport=httpx.MockTransport(overseerr))
    )
    request = await seerr.request_for(862)
    assert request is not None and request.id == 41  # the movie's, not the series'


async def test_a_refusal_tells_the_services_own_message():
    def refuse(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "Unknown query parameter 'x'"})

    seerr = SeerrClient("http://seerr:5055", "key", httpx.AsyncClient(transport=httpx.MockTransport(refuse)))
    with pytest.raises(ServiceError, match="HTTP 400: Unknown query parameter 'x'"):
        await seerr.request_for(1)


async def test_seerr_finds_the_request_of_a_movie_read_only():
    rec = Recorder({("GET", "/api/v1/request"): payload("seerr_requests.json")})
    seerr = SeerrClient("http://seerr:5055", "key", rec.client())
    request = await seerr.request_for(862)
    assert request is not None
    assert (request.id, request.status, request.requested_by) == (41, "approved", "Alice")
    assert await seerr.request_for(12345) is None
    assert request.requested_at == datetime(2026, 11, 8, 10, 0, tzinfo=UTC)


async def test_seerr_reads_every_movie_request_in_one_pass():
    older = {
        "id": 30,
        "status": 5,
        "createdAt": "2025-01-02T10:00:00.000Z",
        "type": "movie",
        "media": {"tmdbId": 862},
        "requestedBy": {"displayName": "Bob"},
    }
    body = payload("seerr_requests.json")
    body["results"].append(older)
    rec = Recorder({("GET", "/api/v1/request"): body})
    latest = await SeerrClient("http://seerr:5055", "key", rec.client()).movie_requests()
    assert set(latest) == {862, 949}
    assert (latest[862].requested_by, latest[862].id) == ("Alice", 41)  # the latest request, not Bob's
    assert len(rec.requests) == 1  # one page holds them all
    assert {r.method for r in rec.requests} == {"GET"}
