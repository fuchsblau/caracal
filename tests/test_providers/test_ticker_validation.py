"""Tests for ticker format validation."""

from caracal.providers.types import validate_ticker_format


class TestTickerValidation:
    def test_valid_simple_ticker(self):
        assert validate_ticker_format("AAPL") is True

    def test_valid_ticker_with_dot(self):
        assert validate_ticker_format("BRK.B") is True

    def test_valid_ticker_with_exchange_suffix(self):
        assert validate_ticker_format("SAP.DE") is True

    def test_valid_single_char(self):
        assert validate_ticker_format("A") is True

    def test_valid_numeric_ticker(self):
        assert validate_ticker_format("1234") is True

    def test_valid_max_length(self):
        assert validate_ticker_format("A" * 12) is True

    def test_invalid_empty_string(self):
        assert validate_ticker_format("") is False

    def test_invalid_special_characters(self):
        assert validate_ticker_format("a]b$c") is False

    def test_invalid_too_long(self):
        assert validate_ticker_format("A" * 20) is False

    def test_invalid_contains_space(self):
        assert validate_ticker_format("DROP TABLE") is False

    def test_invalid_lowercase(self):
        assert validate_ticker_format("aapl") is False

    def test_invalid_hyphen(self):
        assert validate_ticker_format("BRK-B") is False
