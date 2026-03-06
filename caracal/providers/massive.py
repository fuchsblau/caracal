"""Massive.com (formerly Polygon.io) market data provider."""

from datetime import UTC, date, datetime

import pandas as pd

from caracal.providers.types import ProviderError, TickerNotFoundError

try:
    from massive import RESTClient
except ImportError:
    raise ImportError(
        "Massive.com provider requires the 'massive' package. "
        "Install with: pip install caracal-trading[massive]"
    ) from None


class MassiveProvider:
    """Fetch market data from Massive.com REST API."""

    def __init__(self, api_key: str = "", **kwargs):
        if not api_key:
            raise ProviderError(
                "Massive.com requires an API key. "
                "Add [providers.massive] with api_key to ~/.caracal/config.toml "
                "or set CARACAL_MASSIVE_API_KEY"
            )
        self._client = RESTClient(api_key=api_key)

    @property
    def name(self) -> str:
        return "massive"

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        try:
            aggs = list(self._client.list_aggs(
                ticker=ticker,
                multiplier=1,
                timespan="day",
                from_=start_date.isoformat(),
                to=end_date.isoformat(),
                adjusted=True,
            ))
        except Exception:
            raise ProviderError(
                f"Failed to fetch data for {ticker}"
            ) from None

        if not aggs:
            raise TickerNotFoundError(ticker)

        rows = []
        for agg in aggs:
            dt = datetime.fromtimestamp(
                agg.timestamp / 1000, tz=UTC
            ).date()
            rows.append({
                "date": dt,
                "open": float(agg.open),
                "high": float(agg.high),
                "low": float(agg.low),
                "close": float(agg.close),
                "volume": int(agg.volume),
            })

        df = pd.DataFrame(rows)
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def validate_ticker(self, ticker: str) -> bool:
        try:
            details = self._client.get_ticker_details(ticker=ticker)
            return bool(details.ticker)
        except Exception:
            return False
