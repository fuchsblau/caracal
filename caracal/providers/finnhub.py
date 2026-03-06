"""Finnhub market data provider (no adjusted close)."""

from datetime import date, datetime, time

import pandas as pd
import requests

from caracal.providers.types import OHLCV_COLUMNS, ProviderError, TickerNotFoundError

_API_BASE = "https://finnhub.io/api/v1"


class FinnhubProvider:
    """Fetch market data from Finnhub REST API."""

    def __init__(self, api_key: str = "", **kwargs) -> None:
        if not api_key:
            raise ProviderError(
                "Finnhub requires an API key. "
                "Set [providers.finnhub] api_key in config.toml "
                "or CARACAL_FINNHUB_API_KEY env var."
            )
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "finnhub"

    def fetch_ohlcv(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        params = {
            "symbol": ticker,
            "resolution": "D",
            "from": int(datetime.combine(start_date, time.min).timestamp()),
            "to": int(datetime.combine(end_date, time.max).timestamp()),
            "token": self._api_key,
        }
        try:
            resp = requests.get(
                f"{_API_BASE}/stock/candle", params=params, timeout=30
            )
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            code = getattr(resp, "status_code", None)
            if code == 429:
                raise ProviderError(
                    "Finnhub API rate limit exceeded"
                ) from None
            raise ProviderError(
                f"Finnhub API request failed (HTTP {code})"
            ) from None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ProviderError(
                "Network error while connecting to Finnhub"
            ) from None
        except requests.exceptions.RequestException:
            raise ProviderError(
                "Failed to connect to Finnhub API"
            ) from None

        data = resp.json()

        if data.get("s") != "ok":
            raise TickerNotFoundError(ticker)

        try:
            df = pd.DataFrame({
                "date": [date.fromtimestamp(t) for t in data["t"]],
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
                "volume": data["v"],
            })
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                f"Unexpected response format from Finnhub for {ticker}"
            ) from exc

        return df[OHLCV_COLUMNS]

    def validate_ticker(self, ticker: str) -> bool:
        try:
            today = date.today()
            self.fetch_ohlcv(ticker, today, today)
            return True
        except (TickerNotFoundError, ProviderError):
            return False
