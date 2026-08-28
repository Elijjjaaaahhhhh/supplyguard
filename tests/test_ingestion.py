from pathlib import Path

import pytest

from supplyguard.ingestion.retail import convert_value


class FakeArray:
    def tolist(self):
        return [1, 2, 3]


def test_convert_value_converts_array_like_object():
    value = FakeArray()

    result = convert_value(value)

    assert result == [1, 2, 3]


def test_convert_value_keeps_scalar_value():
    value = 42

    result = convert_value(value)

    assert result == 42