"""Process configuration: where Triage keeps its data and how it serves.

Everything the owner configures lives in the database (see ``core.settings``); this is only
what the container needs before the database exists.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class RuntimeConfig:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("TRIAGE_DATA_DIR", "/config")))
    host: str = field(default_factory=lambda: os.environ.get("TRIAGE_HOST", "0.0.0.0"))  # noqa: S104
    port: int = field(default_factory=lambda: int(os.environ.get("TRIAGE_PORT", "9393")))
    log_level: str = field(default_factory=lambda: os.environ.get("TRIAGE_LOG_LEVEL", "INFO"))
    demo: bool = field(default_factory=lambda: os.environ.get("TRIAGE_DEMO", "") in ("1", "true", "yes"))
    static_dir: Path | None = field(
        default_factory=lambda: Path(p) if (p := os.environ.get("TRIAGE_STATIC_DIR")) else None
    )

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.data_dir / 'triage.db'}"
