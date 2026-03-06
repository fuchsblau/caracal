from caracal.providers.types import ProviderError, RateLimitError, TickerNotFoundError


def test_provider_error_is_exception():
    err = ProviderError("API down")
    assert isinstance(err, Exception)
    assert str(err) == "API down"


def test_ticker_not_found_error():
    err = TickerNotFoundError("XYZ123")
    assert isinstance(err, ProviderError)
    assert "XYZ123" in str(err)


class TestRateLimitError:
    def test_basic_message(self):
        err = RateLimitError("Finnhub")
        assert "Finnhub" in str(err)
        assert "rate limit" in str(err).lower()

    def test_retry_after(self):
        err = RateLimitError("Finnhub", retry_after=60)
        assert "60" in str(err)
        assert err.retry_after == 60

    def test_is_provider_error(self):
        err = RateLimitError("Finnhub")
        assert isinstance(err, ProviderError)

    def test_no_retry_after(self):
        err = RateLimitError("Alpha Vantage")
        assert err.retry_after is None
        assert "retry after" not in str(err)

    def test_provider_name_in_message(self):
        for name in ("Finnhub", "Alpha Vantage", "EODHD"):
            err = RateLimitError(name)
            assert name in str(err)
