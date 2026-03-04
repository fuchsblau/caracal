"""Technical indicators."""

from typing import Protocol

import pandas as pd


class Indicator(Protocol):
    """Interface for technical indicators."""

    @property
    def name(self) -> str: ...

    def calculate(self, df: pd.DataFrame) -> pd.Series: ...
