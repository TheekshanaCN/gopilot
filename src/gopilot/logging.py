from __future__ import annotations

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

_session_id: ContextVar[str | None] = ContextVar("session_id", default=None)


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "session_id": getattr(record, "session_id", None) or _session_id.get(),
        }
        return json.dumps(payload)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def set_session_id(session_id: str | None) -> None:
    _session_id.set(session_id)


def get_logger(name: str) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logging.getLogger(name), {"session_id": _session_id.get()})
