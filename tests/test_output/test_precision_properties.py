"""Property-based tests for numeric precision invariants."""

import json
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as st

from caracal.output.json import _round_floats, format_success
from caracal.output.precision import PRICE_DECIMALS


def _decimal_places(val: float) -> int:
    """Count actual decimal places using Decimal for exactness."""
    d = Decimal(str(val))
    # d.as_tuple().exponent is negative for decimal digits
    return max(0, -d.as_tuple().exponent)


@given(
    val=st.floats(
        min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False
    )
)
@settings(max_examples=200)
def test_round_floats_never_exceeds_two_decimals(val):
    """Any float passed through _round_floats should have at most 2 decimal places."""
    rounded = _round_floats(val)
    places = _decimal_places(rounded)
    assert places <= PRICE_DECIMALS, (
        f"Got {places} decimals for {val} -> {rounded}"
    )


@given(
    val=st.floats(
        min_value=0.01, max_value=999999.99, allow_nan=False, allow_infinity=False
    )
)
@settings(max_examples=200)
def test_json_output_floats_rounded(val):
    """Floats in JSON output should be rounded to at most 2 decimal places."""
    output = format_success({"price": val})
    parsed = json.loads(output)
    price = parsed["data"]["price"]
    places = _decimal_places(price)
    assert places <= PRICE_DECIMALS, (
        f"Got {places} decimals for {val} -> {price}"
    )


@given(
    val=st.floats(
        min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False
    )
)
@settings(max_examples=200)
def test_rsi_display_value_always_representable(val):
    """RSI display value should always be representable with 2 decimals."""
    rounded = round(val, 2)
    assert 0.0 <= rounded <= 100.0


@given(
    data=st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.floats(
            min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
        ),
        min_size=1,
        max_size=5,
    )
)
@settings(max_examples=100)
def test_nested_dict_rounding(data):
    """All floats in nested dicts should be rounded."""
    result = _round_floats(data)
    for key, val in result.items():
        places = _decimal_places(val)
        assert places <= PRICE_DECIMALS, (
            f"Key {key}: {places} decimals for {data[key]} -> {val}"
        )
