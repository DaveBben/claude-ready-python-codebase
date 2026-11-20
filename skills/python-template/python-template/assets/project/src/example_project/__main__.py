"""CLI entry point for example-project."""

import os
import sys

from example_project.logger import setup_logging

# Values of LOG_JSON that turn structured output off.
_FALSEY = {"false", "0", "no", "off"}


def main() -> int:
    """Run the application."""
    setup_logging(
        level=os.environ.get("LOG_LEVEL", "INFO"),
        json_format=os.environ.get("LOG_JSON", "true").lower() not in _FALSEY,
    )

    # TODO: Implement your CLI logic here
    print("example-project v0.1.0")

    return 0


if __name__ == "__main__":
    sys.exit(main())
