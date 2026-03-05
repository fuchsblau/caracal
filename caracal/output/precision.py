"""Decimal precision constants for output formatting.

Central source of truth for numeric formatting across all output modes
(human-readable tables and JSON). Currently tuned for stock/equity markets
(2 decimal places). Extend for other asset classes (crypto, forex) by
replacing constants with asset-class-aware functions.
"""

# Prices: close, open, high, low, SMA, EMA, Bollinger bands
PRICE_DECIMALS = 2

# Percentages: change_pct, confidence
PERCENT_DECIMALS = 2

# Ratios/Oscillators: RSI (0-100), MACD, MACD signal, histogram
INDICATOR_DECIMALS = 2

# Volume: always integer
VOLUME_DECIMALS = 0
