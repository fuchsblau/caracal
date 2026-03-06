"""EODHD market data provider."""

from datetime import date

import pandas as pd
import requests

from caracal.providers.types import (
    OHLCV_COLUMNS,
    ProviderError,
    TickerNotFoundError,
    sanitize_url,
)

_API_BASE = "https://eodhd.com/api"


class EODHDProvider:
    """Fetch market data from EODHD REST API."""

    def __init__(
        self, api_key: str = "", default_exchange: str = "US", **kwargs
    ) -> None:
        if not api_key:
            raise ProviderError(
                "EODHD requires an API key. "
                "Set [providers.eodhd] api_key in config.toml "
                "or CARACAL_EODHD_API_KEY env var."
            )
        self._api_key = api_key
        self._default_exchange = default_exchange

    @property
    def name(self) -> str:
        return "eodhd"

    def _resolve_ticker(self, ticker: str) -> str:
        """Append default exchange if no suffix present."""
        if "." not in ticker:
            return f"{ticker}.{self._default_exchange}"
        return ticker

    def fetch_ohlcv(
        self, ticker: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        resolved = self._resolve_ticker(ticker)
        url = f"{_API_BASE}/eod/{resolved}"
        params = {
            "api_token": self._api_key,
            "fmt": "json",
            "from": str(start_date),
            "to": str(end_date),
            "period": "d",
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.HTTPError:
            code = getattr(resp, "status_code", None)
            if code == 429:
                raise ProviderError(
                    "EODHD API rate limit exceeded"
                ) from None
            raise ProviderError(
                f"EODHD API request failed (HTTP {code})"
            ) from None
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            raise ProviderError(
                "Network error while connecting to EODHD"
            ) from None
        except requests.exceptions.RequestException:
            raise ProviderError(
                "Failed to connect to EODHD API"
            ) from None

        data = resp.json()

        if not data or isinstance(data, dict):
            raise TickerNotFoundError(ticker)

        try:
            df = pd.DataFrame(data)
            df = df.drop(columns=["close"])
            df = df.rename(columns={"adjusted_close": "close"})
            df["date"] = pd.to_datetime(df["date"]).dt.date
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(
                f"Unexpected response format from EODHD for {ticker}"
            ) from exc

        return df[OHLCV_COLUMNS].reset_index(drop=True)

    def validate_ticker(self, ticker: str) -> bool:
        try:
            self.fetch_ohlcv(ticker, date.today(), date.today())
            return True
        except (TickerNotFoundError, ProviderError):
            return False
