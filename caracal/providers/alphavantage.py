"""Alpha Vantage market data provider using CSV endpoint."""

import io
from datetime import date

import pandas as pd
import requests

from caracal.providers.types import (
    OHLCV_COLUMNS,
    ProviderError,
    TickerNotFoundError,
    sanitize_url,
)

_API_BASE = "https://www.alphavantage.co/query"


class AlphaVantageProvider:
    """Fetch market data from Alpha Vantage REST API."""

    def __init__(self, api_key: str = "", **kwargs) -> None:
        if not api_key:
            raise ProviderError(
                "Alpha Vantage requires an API key. "
                "Set [providers.alphavantage] api_key in config.toml "
                "or CARACAL_ALPHAVANTAGE_API_KEY env var."
            )
        self._api_key = api_key

    @property
    def name(self) -> str:
        return "alphavantage"

    def fetch_ohlcv(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": ticker,
            "outputsize": "full",
            "apikey": self._api_key,
            "datatype": "csv",
        }
        try:
            resp = requests.get(_API_BASE, params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            code = getattr(resp, "status_code", None)
            if code == 429:
                raise ProviderError(
                    "Alpha Vantage API rate limit exceeded"
                ) from None
            raise ProviderError(
                f"Alpha Vantage API request failed (HTTP {code})"
            ) from None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ProviderError(
                "Network error while connecting to Alpha Vantage"
            ) from None
        except requests.exceptions.RequestException:
            raise ProviderError(
                "Failed to connect to Alpha Vantage API"
            ) from None

        text = resp.text.strip()
        if text.startswith("{"):
            raise ProviderError(
                "Alpha Vantage API error (check API key and rate limits)"
            )

        try:
            df = pd.read_csv(io.StringIO(resp.text))
        except pd.errors.ParserError:
            raise ProviderError(
                "Failed to parse Alpha Vantage response"
            ) from None

        if df.empty:
            raise TickerNotFoundError(ticker)

        try:
            # Use adjusted close as the close price
            df["close"] = df["adjusted_close"]
            df = df.rename(columns={"timestamp": "date"})
            df["date"] = pd.to_datetime(df["date"]).dt.date
            mask = (df["date"] >= start_date) & (df["date"] <= end_date)
            df = df.loc[mask, OHLCV_COLUMNS].sort_values("date").reset_index(
                drop=True
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                f"Unexpected response format from Alpha Vantage for {ticker}"
            ) from exc

        if df.empty:
            raise TickerNotFoundError(ticker)

        return df

    def validate_ticker(self, ticker: str) -> bool:
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": ticker,
            "apikey": self._api_key,
        }
        try:
            resp = requests.get(_API_BASE, params=params, timeout=10)
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise ProviderError(
                f"Alpha Vantage ticker validation failed: {sanitize_url(str(exc))}"
            ) from None
        matches = resp.json().get("bestMatches", [])
        return any(m.get("1. symbol") == ticker for m in matches)
