"""Tests for the JSON logging configuration."""

import json
import logging
import sys
from collections.abc import Iterator

import pytest

from example_project.logger import JsonFormatter, setup_logging


def _record(
    *,
    msg: str = "hello %s",
    args: tuple[object, ...] = ("world",),
    name: str = "example_project.demo",
    level: int = logging.INFO,
    exc_info: object = None,
) -> logging.LogRecord:
    """Build a LogRecord, defaulting everything a test doesn't care about."""
    return logging.LogRecord(
        name=name,
        level=level,
        pathname=__file__,
        lineno=10,
        msg=msg,
        args=args,
        exc_info=exc_info,  # type: ignore[arg-type]
    )


@pytest.fixture
def restore_root_logging() -> Iterator[None]:
    """Snapshot and restore the root logger so setup_logging can't leak state."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


class TestJsonFormatter:
    """The formatter renders one JSON object per record."""

    def test_emits_core_fields(self) -> None:
        payload = json.loads(JsonFormatter().format(_record()))

        assert payload["level"] == "INFO"
        assert payload["logger"] == "example_project.demo"
        assert payload["message"] == "hello world"
        assert "timestamp" in payload

    def test_merges_extra_fields(self) -> None:
        record = _record()
        record.__dict__["request_id"] = "abc-123"

        payload = json.loads(JsonFormatter().format(record))

        assert payload["request_id"] == "abc-123"

    def test_captures_exception_text(self) -> None:
        def _boom() -> None:
            raise ValueError("boom")

        try:
            _boom()
        except ValueError:
            record = _record(exc_info=sys.exc_info())
        else:
            # Without this branch `record` is unbound if _boom() ever stops
            # raising, and the test fails with a NameError instead of saying
            # what actually went wrong.
            pytest.fail("expected _boom() to raise ValueError")

        payload = json.loads(JsonFormatter().format(record))

        assert "ValueError: boom" in payload["exception"]

    def test_extra_cannot_overwrite_core_fields(self) -> None:
        record = _record()
        record.__dict__["level"] = "HIJACKED"
        record.__dict__["logger"] = "HIJACKED"

        payload = json.loads(JsonFormatter().format(record))

        assert payload["level"] == "INFO"
        assert payload["logger"] == "example_project.demo"

    def test_serializes_non_json_extra_as_string(self) -> None:
        record = _record()
        record.__dict__["obj"] = object()

        payload = json.loads(JsonFormatter().format(record))

        assert payload["obj"].startswith("<object object")


class TestSetupLogging:
    """setup_logging wires a single stdout handler onto the root logger."""

    @pytest.mark.usefixtures("restore_root_logging")
    def test_installs_json_formatter_by_default(self) -> None:
        setup_logging(level="DEBUG")
        root = logging.getLogger()

        assert root.level == logging.DEBUG
        assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)

    @pytest.mark.usefixtures("restore_root_logging")
    def test_text_format_uses_plain_formatter(self) -> None:
        setup_logging(json_format=False)
        root = logging.getLogger()

        assert root.handlers, "expected a handler on the root logger"
        formatter = root.handlers[0].formatter
        assert formatter is not None
        assert not isinstance(formatter, JsonFormatter)
        assert " - INFO - hello world" in formatter.format(_record())
