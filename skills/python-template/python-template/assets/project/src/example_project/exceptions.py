"""Custom exceptions for example_project."""


class ExampleProjectError(Exception):
    """Base exception for example_project errors."""


class ConfigurationError(ExampleProjectError):
    """Raised when configuration is invalid."""
