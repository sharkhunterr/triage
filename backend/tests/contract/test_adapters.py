"""Real adapters against recorded payloads (contracts/external-services.md)."""

import json
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
    assert request.url.params["append_to_response"] == "keywords,release_dates,translations"
    assert request.url.params["api_key"] == "v3key"


async def test_tmdb_in_french_gives_the_french_rating_and_synopsis():
    rec = Recorder({("GET", "/3/movie/862"): payload("tmdb_movie.json")})
    details = await TmdbClient("v3key", rec.client(), RateLimiter(1000), language="fr-FR").details(862)
    assert details.certifications == ("U",)
    assert details.overview == "Woody, le jouet préféré d'Andy, voit arriver Buzz l'Éclair."
    assert details.title == "Toy Story : les jouets"
    assert details.genres[0] == "Animation"  # genres stay in English, the language rules are written in


async def test_tmdb_without_a_rating_for_the_country_falls_back_to_the_us_one():
    rec = Recorder({("GET", "/3/movie/862"): payload("tmdb_movie.json")})
    details = await TmdbClient("v3key", rec.client(), RateLimiter(1000), language="de-DE").details(862)
    assert details.certifications == ("G",)
    assert details.overview == "Led by Woody, Andy's toys live happily in his room..."


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


async def test_seerr_finds_the_request_of_a_movie_read_only():
    rec = Recorder({("GET", "/api/v1/request"): payload("seerr_requests.json")})
    seerr = SeerrClient("http://seerr:5055", "key", rec.client())
    request = await seerr.request_for(862)
    assert request is not None
    assert (request.id, request.status, request.requested_by) == (41, "approved", "Alice")
    assert await seerr.request_for(12345) is None
    assert {r.method for r in rec.requests} == {"GET"}
