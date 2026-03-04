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
