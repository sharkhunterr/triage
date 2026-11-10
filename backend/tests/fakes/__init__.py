"""In-memory stand-ins for every external service (Constitution VIII)."""

from dataclasses import dataclass, field

from tests.fakes.ollama import FakeOllama
from tests.fakes.radarr import FakeRadarr
from tests.fakes.seerr import FakeSeerr
from tests.fakes.smtp import FakeMailer
from tests.fakes.tmdb import FakeTmdb
from tests.fakes.wiki import FakeWiki
from triage.adapters.types import Adapters
from triage.core.settings import AppSettings


@dataclass
class Fakes:
    radarr: FakeRadarr | None = field(default_factory=FakeRadarr)
    tmdb: FakeTmdb | None = field(default_factory=FakeTmdb)
    ollama: FakeOllama | None = None
    seerr: FakeSeerr | None = None
    mailer: FakeMailer | None = field(default_factory=FakeMailer)
    wiki: FakeWiki | None = None

    def factory(self, _settings: AppSettings) -> Adapters:
        return Adapters(
            radarr=self.radarr,
            tmdb=self.tmdb,
            ollama=self.ollama,
            seerr=self.seerr,
            mailer=self.mailer,
            wiki=self.wiki,
        )
