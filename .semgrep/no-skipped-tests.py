import sys

import pytest


# ruleid: no-skipped-tests
@pytest.mark.skip(reason="flaky")
def test_skipped_with_reason() -> None:
    assert True


# ruleid: no-skipped-tests
@pytest.mark.skip
def test_skipped_bare() -> None:
    assert True


def test_skipped_inline() -> None:
    # ruleid: no-skipped-tests
    pytest.skip("not today")


# ok: no-skipped-tests
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_conditional() -> None:
    assert True


def test_optional_dependency() -> None:
    # ok: no-skipped-tests
    pytest.importorskip("numpy")
