"""JSON logs, each line carrying the movie / decision / work item being processed."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

radarr_id_var: ContextVar[int | None] = ContextVar("radarr_id", default=None)
decision_id_var: ContextVar[int | None] = ContextVar("decision_id", default=None)
work_item_id_var: ContextVar[int | None] = ContextVar("work_item_id", default=None)

_CONTEXT = (
    ("radarr_id", radarr_id_var),
    ("decision_id", decision_id_var),
    ("work_item_id", work_item_id_var),
)
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, var in _CONTEXT:
            if (value := var.get()) is not None:
                entry[key] = value
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
    for noisy in ("httpx", "httpcore", "aiosqlite", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
