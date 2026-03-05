import json

from caracal.output.json import format_error, format_success


def test_success_envelope():
    result = format_success(
        data={"price": 150.0},
        meta={"ticker": "AAPL", "command": "fetch"},
    )
    parsed = json.loads(result)
    assert parsed["status"] == "success"
    assert parsed["data"]["price"] == 150.0
    assert parsed["meta"]["ticker"] == "AAPL"
    assert "timestamp" in parsed["meta"]


def test_error_envelope():
    result = format_error(
        code="INVALID_TICKER",
        message="Ticker 'XYZ' not found",
        meta={"command": "fetch"},
    )
    parsed = json.loads(result)
    assert parsed["status"] == "error"
    assert parsed["error"]["code"] == "INVALID_TICKER"
    assert parsed["error"]["message"] == "Ticker 'XYZ' not found"
    assert "timestamp" in parsed["meta"]


def test_success_envelope_without_meta():
    result = format_success(data={"ok": True})
    parsed = json.loads(result)
    assert parsed["status"] == "success"
    assert "meta" in parsed


def test_success_envelope_rounds_floats():
    """Float values in JSON should be rounded to 2 decimal places."""
    result = format_success(
        data={"price": 178.72000122070312, "volume": 1000000},
        meta={"ticker": "AAPL"},
    )
    parsed = json.loads(result)
    assert parsed["data"]["price"] == 178.72
    assert parsed["data"]["volume"] == 1000000


def test_success_envelope_rounds_nested_floats():
    """Nested float values should also be rounded."""
    result = format_success(
        data={
            "indicators": {
                "sma_20": 178.345678,
                "rsi_14": 38.219999,
            }
        },
    )
    parsed = json.loads(result)
    assert parsed["data"]["indicators"]["sma_20"] == 178.35
    assert parsed["data"]["indicators"]["rsi_14"] == 38.22
