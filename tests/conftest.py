"""Shared pytest configuration.

Hypothesis profiles. Without a registered profile the suite runs Hypothesis's
default (100 examples, a 200ms per-example deadline), which is slow enough to
discourage property tests locally and shallow enough to miss things in CI. Two
profiles split that: a fast one for the edit-test-edit loop, a thorough one for
the gate.

Selected with the HYPOTHESIS_PROFILE environment variable; the CI workflow sets
it to "ci". A property test that fails only under the ci profile is still a real
failure: reproduce it locally with

    HYPOTHESIS_PROFILE=ci uv run pytest path/to/test.py
"""

import os

from hypothesis import HealthCheck, settings

# Enough examples to catch the obvious edge cases without slowing the loop.
settings.register_profile("dev", max_examples=20)

# deadline=None: CI runners are noisy neighbours, and a per-example timeout
# turns that noise into a flaky failure that says nothing about the code.
# The example count, not the clock, is what makes this profile thorough.
settings.register_profile(
    "ci",
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
