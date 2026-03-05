"""Tests for precision constants."""

from caracal.output.precision import (
    INDICATOR_DECIMALS,
    PERCENT_DECIMALS,
    PRICE_DECIMALS,
    VOLUME_DECIMALS,
)


def test_price_decimals_is_two():
    assert PRICE_DECIMALS == 2


def test_percent_decimals_is_two():
    assert PERCENT_DECIMALS == 2


def test_indicator_decimals_is_two():
    assert INDICATOR_DECIMALS == 2


def test_volume_decimals_is_zero():
    assert VOLUME_DECIMALS == 0
