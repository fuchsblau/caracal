"""Tests for URL sanitization utility."""

from caracal.providers.types import sanitize_url


class TestSanitizeUrl:
    def test_masks_api_key_param(self):
        url = "https://api.example.com?apikey=SECRET123&symbol=AAPL"
        result = sanitize_url(url)
        assert "SECRET123" not in result
        assert "apikey=***" in result

    def test_masks_token_param(self):
        url = "https://finnhub.io/api/v1/stock/candle?token=MY_SECRET&symbol=AAPL"
        result = sanitize_url(url)
        assert "MY_SECRET" not in result
        assert "token=***" in result

    def test_masks_api_token_param(self):
        url = "https://eodhd.com/api/eod/AAPL.US?api_token=SECRET&fmt=json"
        result = sanitize_url(url)
        assert "SECRET" not in result
        assert "api_token=***" in result

    def test_preserves_non_secret_params(self):
        url = "https://api.example.com?symbol=AAPL&apikey=SECRET"
        result = sanitize_url(url)
        assert "symbol=AAPL" in result

    def test_masks_apikey_case_insensitive(self):
        url = "https://api.example.com?APIKEY=SECRET&symbol=AAPL"
        result = sanitize_url(url)
        assert "SECRET" not in result

    def test_preserves_url_structure(self):
        url = "https://api.example.com/path?apikey=SECRET&symbol=AAPL"
        result = sanitize_url(url)
        assert result.startswith("https://api.example.com/path?")

    def test_url_without_secrets_unchanged(self):
        url = "https://api.example.com?symbol=AAPL&period=d"
        result = sanitize_url(url)
        assert result == url

    def test_masks_secret_param(self):
        url = "https://api.example.com?secret=TOP_SECRET&data=1"
        result = sanitize_url(url)
        assert "TOP_SECRET" not in result
        assert "secret=***" in result
