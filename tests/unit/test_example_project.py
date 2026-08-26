"""Tests for example_project."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from example_project.exceptions import (
    ConfigurationError,
    ExampleProjectError,
)


class TestExceptionHierarchy:
    """Tests for exception inheritance."""

    def test_configuration_error_inherits_from_base(self) -> None:
        assert issubclass(ConfigurationError, ExampleProjectError)

    def test_base_error_inherits_from_exception(self) -> None:
        assert issubclass(ExampleProjectError, Exception)


@pytest.mark.property
@given(message=st.text())
def test_error_carries_message_for_any_input(message: str) -> None:
    """A raised error round-trips its message and keeps the base type.

    Property-based (hypothesis) example: instead of one hand-picked string, this
    asserts the invariant across many generated inputs — empty strings, unicode,
    control characters — the edge cases a single literal example would miss.
    """
    error = ConfigurationError(message)

    assert str(error) == message
    assert isinstance(error, ExampleProjectError)
