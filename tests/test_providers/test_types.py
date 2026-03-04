from caracal.providers.types import ProviderError, TickerNotFoundError


def test_provider_error_is_exception():
    err = ProviderError("API down")
    assert isinstance(err, Exception)
    assert str(err) == "API down"


def test_ticker_not_found_error():
    err = TickerNotFoundError("XYZ123")
    assert isinstance(err, ProviderError)
    assert "XYZ123" in str(err)
