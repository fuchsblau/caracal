"""Interactive Brokers market data provider via ib_async."""

import logging
from datetime import date

import pandas as pd

from caracal.providers.types import ProviderError, TickerNotFoundError

logger = logging.getLogger("caracal")

try:
    from ib_async import IB, Stock, util
except ImportError:
    raise ImportError(
        "IBKR provider requires the 'ib_async' package. "
        "Install with: pip install caracal-trading[ibkr]"
    ) from None


class IBKRProvider:
    """Fetch market data from Interactive Brokers via TWS/Gateway."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: str = "7497",
        client_id: str = "1",
        **kwargs,
    ):
        self._host = host
        self._port = int(port)
        self._client_id = int(client_id)
        self._ib = IB()

    @property
    def name(self) -> str:
        return "ibkr"

    def _connect(self):
        if not self._ib.isConnected():
            try:
                self._ib.connect(
                    self._host, self._port, clientId=self._client_id
                )
            except Exception:
                logger.debug(
                    "IBKR connection error for %s:%s",
                    self._host,
                    self._port,
                    exc_info=True,
                )
                raise ProviderError(
                    f"Cannot connect to TWS/Gateway at "
                    f"{self._host}:{self._port}. "
                    "Ensure TWS or IB Gateway is running."
                ) from None

    def fetch_ohlcv(
        self,
        ticker: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        self._connect()

        contract = Stock(ticker, "SMART", "USD")
        duration_days = (end_date - start_date).days
        duration_str = f"{duration_days} D"

        try:
            bars = self._ib.reqHistoricalData(
                contract,
                endDateTime=end_date.strftime("%Y%m%d %H:%M:%S"),
                durationStr=duration_str,
                barSizeSetting="1 day",
                whatToShow="TRADES",
                useRTH=True,
                formatDate=1,
            )
        except Exception:
            logger.debug("Provider error details for %s", ticker, exc_info=True)
            raise ProviderError(
                f"Failed to fetch data for {ticker}"
            ) from None

        if not bars:
            raise TickerNotFoundError(ticker)

        df = util.df(bars)

        # Normalize to standard schema
        df = df.rename(columns=str.lower)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"]).dt.date

        # Keep only standard OHLCV columns
        cols = [
            c
            for c in ["date", "open", "high", "low", "close", "volume"]
            if c in df.columns
        ]
        df = df[cols]
        df = df.sort_values("date").reset_index(drop=True)
        return df

    def validate_ticker(self, ticker: str) -> bool:
        self._connect()
        try:
            contract = Stock(ticker, "SMART", "USD")
            qualified = self._ib.qualifyContracts(contract)
            return len(qualified) > 0 and qualified[0].conId > 0
        except Exception:
            return False
