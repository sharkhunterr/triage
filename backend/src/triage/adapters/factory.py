"""Build the adapters from the current settings. The app holds one factory (sharing one HTTP
client, closed with the app); tests swap it for fakes."""

from collections.abc import Callable

import httpx

from triage.adapters.ollama import OllamaClient
from triage.adapters.radarr import RadarrClient
from triage.adapters.seerr import SeerrClient
from triage.adapters.smtp import SmtpMailer
from triage.adapters.tmdb import TmdbClient
from triage.adapters.types import Adapters
from triage.adapters.wiki import WikiClient
from triage.core.settings import AppSettings

AdapterFactory = Callable[[AppSettings], Adapters]


def make_factory(client: httpx.AsyncClient) -> AdapterFactory:
    def build(settings: AppSettings) -> Adapters:
        return build_adapters(settings, client)

    return build


def build_adapters(settings: AppSettings, client: httpx.AsyncClient) -> Adapters:
    s = settings
    return Adapters(
        radarr=RadarrClient(s.radarr.url, s.radarr.api_key, client) if s.radarr_configured else None,
        tmdb=TmdbClient(s.tmdb.api_key, client, language=s.tmdb.language) if s.tmdb.api_key else None,
        # built from the address alone, to test it and list its models; the AI is asked only once a
        # model is chosen too (settings.ai_enabled)
        ollama=(
            OllamaClient(s.ollama.url, s.ollama.model, s.ollama.timeout_s, client, thinking=s.ollama.thinking)
            if s.ollama.url
            else None
        ),
        seerr=SeerrClient(s.seerr.url, s.seerr.api_key, client) if s.seerr_configured else None,
        mailer=(
            SmtpMailer(
                s.smtp.host, s.smtp.port, s.smtp.security, s.smtp.username, s.smtp.password, s.smtp.sender
            )
            if s.email_enabled
            else None
        ),
        wiki=WikiClient(client, s.tmdb.language) if s.wiki.enabled and s.tmdb.api_key else None,
    )
