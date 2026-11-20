import sys
import unittest

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


class CaseSkips(unittest.TestCase):
    # ruleid: no-skipped-tests
    @unittest.skip("flaky")
    def test_decorator_skip(self) -> None:
        assert True

    def test_inline_skip(self) -> None:
        # ruleid: no-skipped-tests
        self.skipTest("not today")

    def test_raises_skip(self) -> None:
        # ruleid: no-skipped-tests
        raise unittest.SkipTest("not today")

    # ok: no-skipped-tests
    @unittest.skipIf(sys.platform == "win32", "POSIX only")
    def test_conditional_skip(self) -> None:
        assert True
