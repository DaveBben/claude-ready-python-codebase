import unittest
from unittest import mock

import pytest


def total(lines: list[int]) -> int:
    return sum(lines)


# ruleid: no-assertless-tests
def test_calls_only() -> None:
    total([1, 2])


# ruleid: no-assertless-tests
def test_assert_in_the_name_only() -> None:
    total([])


# ruleid: no-assertless-tests
def test_prints_the_result() -> None:
    print(total([1]))


# ok: no-assertless-tests
def test_asserts() -> None:
    assert total([1, 2]) == 3


# ok: no-assertless-tests
def test_asserts_in_a_loop() -> None:
    for n in (1, 2):
        assert total([n]) == n


# ok: no-assertless-tests
def test_raises() -> None:
    with pytest.raises(TypeError):
        total(None)  # type: ignore[arg-type]


def _assert_sums(lines: list[int], want: int) -> None:
    assert total(lines) == want


# ok: no-assertless-tests
def test_uses_an_asserting_helper() -> None:
    _assert_sums([2, 2], 4)


# ok: no-assertless-tests
def test_mock_assertion() -> None:
    m = mock.Mock()
    m(1)
    m.assert_called_once_with(1)


class TotalCase(unittest.TestCase):
    # ok: no-assertless-tests
    def test_unittest_assert(self) -> None:
        self.assertEqual(total([1]), 1)

    # ruleid: no-assertless-tests
    def test_unittest_nothing(self) -> None:
        total([1])
