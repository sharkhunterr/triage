"""The owner's settings: typed, validated, stored as one JSON document.

Secrets stay on the server (Constitution VII): ``public_view`` replaces each of them with
``{"set": bool}``, and an update only replaces a secret when a new value is given.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from triage.models import Setting

SETTINGS_KEY = "app"


class RadarrSettings(BaseModel):
    url: str = ""
    api_key: str = ""
    intake_root_folders: list[str] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("intake_root_folders")
    @classmethod
    def _folders(cls, value: list[str]) -> list[str]:
        return sorted({normalize_folder(v) for v in value if v.strip()})


class TmdbSettings(BaseModel):
    api_key: str = ""
    # language-COUNTRY: the synopsis language and the country whose age ratings are kept
    language: str = Field("en-US", pattern=r"^[a-z]{2}-[A-Z]{2}$")


class OllamaSettings(BaseModel):
    url: str = ""
    model: str = ""
    timeout_s: int = Field(180, ge=5, le=600)  # a CPU-only Ollama loads the model before answering
    # when_unsure: only when the rules are not conclusive; always: a second opinion on every movie
    ask: Literal["when_unsure", "always", "never"] = "when_unsure"
    # a reasoning pass before the verdict: closer on hard cases, but minutes per movie on a CPU
    thinking: bool = False

    @field_validator("url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip().rstrip("/")


class SeerrSettings(BaseModel):
    url: str = ""
    api_key: str = ""
    webhook_secret: str = ""

    @field_validator("url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip().rstrip("/")


class SmtpSettings(BaseModel):
    host: str = ""
    port: int = Field(587, ge=1, le=65535)
    security: Literal["starttls", "ssl", "none"] = "starttls"
    username: str = ""
    password: str = ""
    sender: str = ""
    recipient: str = ""


class SortingSettings(BaseModel):
    mode: Literal["preview", "automatic"] = "preview"
    threshold: float = Field(0.80, ge=0.5, le=1.0)
    margin: int = Field(20, ge=0, le=100)
    ai_weight: int = Field(60, ge=0, le=100)
    poll_interval_s: int = Field(300, ge=60, le=86400)
    link_validity_days: int = Field(7, ge=1, le=30)


class WikiSettings(BaseModel):
    # what kind of work each movie is (Wikidata) and its Wikipedia opening, for the rules and the AI
    enabled: bool = False


class AppSettings(BaseModel):
    # False until the owner finishes (or skips) the setup wizard; set back to False to reopen it.
    wizard_completed: bool = False
    base_url: str = ""
    radarr: RadarrSettings = Field(default_factory=RadarrSettings)
    tmdb: TmdbSettings = Field(default_factory=TmdbSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    seerr: SeerrSettings = Field(default_factory=SeerrSettings)
    smtp: SmtpSettings = Field(default_factory=SmtpSettings)
    sorting: SortingSettings = Field(default_factory=SortingSettings)
    wiki: WikiSettings = Field(default_factory=WikiSettings)

    @field_validator("base_url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @property
    def radarr_configured(self) -> bool:
        return bool(self.radarr.url and self.radarr.api_key)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ollama.url and self.ollama.model)

    @property
    def email_enabled(self) -> bool:
        return bool(self.smtp.host and self.smtp.recipient and self.smtp.sender)

    @property
    def seerr_configured(self) -> bool:
        return bool(self.seerr.url and self.seerr.api_key)


SECRETS: dict[str, tuple[str, ...]] = {
    "radarr": ("api_key",),
    "tmdb": ("api_key",),
    "seerr": ("api_key", "webhook_secret"),
    "smtp": ("password",),
}


def normalize_folder(path: str) -> str:
    """Radarr root folders compare without their trailing slash."""
    path = path.strip()
    return path.rstrip("/") or "/"


def same_folder(a: str | None, b: str | None) -> bool:
    return a is not None and b is not None and normalize_folder(a) == normalize_folder(b)


def public_view(settings: AppSettings) -> dict[str, Any]:
    data = settings.model_dump()
    for section, keys in SECRETS.items():
        for key in keys:
            data[section][key] = {"set": bool(data[section][key])}
    return data


def merge_update(current: AppSettings, update: dict[str, Any]) -> AppSettings:
    """Apply a partial update. A secret given as a non-empty string replaces the stored one;
    given as ``""`` it is cleared; absent (or ``{"set": …}``) it is kept."""
    data = current.model_dump()
    for key, value in update.items():
        if key not in data:
            continue
        if isinstance(value, dict) and isinstance(data[key], dict):
            for sub, sub_value in value.items():
                if sub not in data[key]:
                    continue
                if sub in SECRETS.get(key, ()) and not isinstance(sub_value, str):
                    continue
                data[key][sub] = sub_value
        else:
            data[key] = value
    return AppSettings.model_validate(data)


async def load_settings(session: AsyncSession) -> AppSettings:
    row = await session.get(Setting, SETTINGS_KEY)
    return AppSettings.model_validate(row.value) if row else AppSettings()


async def save_settings(session: AsyncSession, settings: AppSettings) -> None:
    row = await session.get(Setting, SETTINGS_KEY)
    if row is None:
        session.add(Setting(key=SETTINGS_KEY, value=settings.model_dump()))
    else:
        row.value = settings.model_dump()
    await session.flush()
