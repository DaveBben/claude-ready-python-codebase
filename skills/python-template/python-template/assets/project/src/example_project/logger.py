"""Logging configuration with structured JSON output (standard library only)."""

import datetime as dt
import json
import logging
import sys
from typing import Any

__all__ = ["JsonFormatter", "setup_logging"]

_TEXT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# LogRecord attributes that are not caller-supplied context. Anything on the
# record outside this set arrived via ``logger.info(..., extra={...})`` and is
# merged into the JSON so structured fields survive.
_RESERVED = frozenset(
    {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
        "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
        "created", "msecs", "relativeCreated", "thread", "threadName",
        "processName", "process", "taskName", "message", "asctime",
    }
)  # fmt: skip


class JsonFormatter(logging.Formatter):
    """Render a log record as a single line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": dt.datetime.fromtimestamp(
                record.created, tz=dt.UTC
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Merge any ``extra={...}`` fields the caller attached, but never let one
        # overwrite a core field (a stray extra named "level" must not win).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and key not in payload:
                payload[key] = value

        # Keep exception and stack context — dropping it would lose the error.
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        # default=str stops a non-serializable extra from crashing the handler.
        return json.dumps(payload, default=str)


def setup_logging(*, level: str = "INFO", json_format: bool = True) -> None:
    """Configure root logging for the application.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True (default), emit one JSON object per line to stdout.
            Set False for a human-readable text format during local development.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter()
        if json_format
        else logging.Formatter(_TEXT_FORMAT, _DATE_FORMAT)
    )
    # force=True replaces any handlers a prior call or import already installed.
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
