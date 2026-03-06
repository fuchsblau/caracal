# Caracal

```
░█▀▀░█▀█░█▀▄░█▀█░█▀▀░█▀█░█░░
░█░░░█▀█░█▀▄░█▀█░█░░░█▀█░█░░
░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀░▀░▀░▀▀▀
```

**An opinionated terminal UI for stock analysis.**

[![CI](https://github.com/fuchsblau/caracal/actions/workflows/ci.yml/badge.svg)](https://github.com/fuchsblau/caracal/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/caracal-trading)](https://pypi.org/project/caracal-trading/)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=fuchsblau_caracal&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=fuchsblau_caracal)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=fuchsblau_caracal&metric=coverage)](https://sonarcloud.io/summary/new_code?id=fuchsblau_caracal)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Caracal is a keyboard-driven terminal app for tracking stocks, running technical analysis, and making entry point decisions — without leaving your terminal. No browser, no cloud account, no subscription. Install it, point it at a ticker, and go.

> **This is not financial advice.** Caracal is for informational and educational purposes only. Do your own research. See [full disclaimer](#disclaimer).

## Opinions

Caracal makes choices so you don't have to:

- **Dark theme, no light mode.** A One Dark-inspired palette designed for long sessions. Cyan for prices, green/red for changes, purple accents. Not configurable — because we spent the time getting it right.
- **Vim keys, no mouse.** `j`/`k` to move, `Enter` to drill in, `Esc` to go back, `q` to quit. If you use a terminal, you already know how this works.
- **Local-first, always.** Your market data lives in a DuckDB file on your machine. No accounts, no telemetry, no API we control. You own your data.
- **Indicators with interpretation.** Not just numbers — color-coded signals that tell you RSI is overbought or MACD is crossing. Grouped by category: Trend, Momentum, Volatility.
- **Six providers, one interface.** Yahoo Finance, Alpha Vantage, EODHD, Finnhub, Massive, Interactive Brokers. Swap freely — the experience stays the same.

## Install

```bash
pip install caracal-trading[all]
caracal init
caracal tui
```

That's it. Watchlists, indicators, entry signals — all in your terminal.

Or pick only the provider you need:

```bash
pip install caracal-trading[yahoo,tui]       # Yahoo Finance — free, no key needed
pip install caracal-trading[alphavantage,tui] # Alpha Vantage — free tier available
pip install caracal-trading[eodhd,tui]        # EODHD — broad exchange coverage
pip install caracal-trading[finnhub,tui]      # Finnhub — real-time US data
pip install caracal-trading[massive,tui]      # Massive.com — professional data
pip install caracal-trading[ibkr,tui]         # Interactive Brokers — existing account
```

Requires Python 3.12+.

## The TUI

Launch with `caracal tui`. Everything is keyboard-driven:

| Key | Action |
|-----|--------|
| `j` / `k` | Navigate up/down |
| `Enter` | Open stock detail view |
| `Esc` | Go back |
| `r` | Refresh market data |
| `w` | Switch watchlist |
| `c` | Create watchlist |
| `d` | Delete watchlist |
| `a` | Add tickers (batch: `AAPL MSFT GOOGL`) |
| `x` | Remove ticker |
| `i` | App info |
| `q` | Quit |

### Watchlist View

Your main workspace. Each watchlist is a tab showing:

| Column | What it tells you |
|--------|-------------------|
| Symbol | Ticker |
| Name | Company name |
| Price | Latest close in cyan |
| Chg% | Daily change — green if up, red if down |
| Signal | BUY / HOLD / SELL — color-coded |
| Conf | Confidence score for the signal |
| RSI | Relative Strength Index with overbought/oversold markers |
| MACD | Trend momentum at a glance |
| BB | Bollinger Band position |

### Detail View

Press `Enter` on any ticker. Indicators grouped by what they measure:

- **Trend** — SMA 20/50, EMA 12 with crossover interpretation
- **Momentum** — RSI 14, MACD with signal line and histogram
- **Volatility** — Bollinger Bands with position and bandwidth

Each indicator shows a color-coded interpretation: `▲ Bullish`, `▼ Bearish`, or `— Neutral`. The header breaks down the entry signal into vote counts — you see exactly why it says "BUY" (e.g., 3 buy / 1 hold / 1 sell).

Last 5 days of OHLCV data at the bottom for recent price context.

## The CLI

The TUI is the primary interface, but Caracal has a full CLI for scripting and automation:

```bash
caracal fetch AAPL                   # fetch OHLCV data (delta-fetch — only new data)
caracal fetch MSFT --period 2y       # custom period
caracal analyze AAPL                 # technical indicators
caracal entry AAPL                   # entry signal with confidence
caracal --format json entry AAPL     # structured JSON for piping
```

```
$ caracal entry AAPL
AAPL: BUY (confidence: 72.00%)
  sma_20: 178.34    sma_50: 175.12    ema_12: 179.05
  rsi_14: 38.21     macd: 1.23        macd_signal: 0.98
  bollinger_upper: 185.42             bollinger_lower: 170.86
```

### Watchlist CLI

```bash
caracal watchlist create tech
caracal watchlist add tech AAPL MSFT GOOGL NVDA AMZN
caracal watchlist show tech
caracal watchlist list
```

### Configuration

```bash
caracal init          # create default config
caracal configure     # interactive wizard
```

Config lives in `~/.caracal/config.toml`. Provider keys can also be set via environment variables (`CARACAL_ALPHAVANTAGE_API_KEY`, etc.). Priority: defaults → config → env vars → CLI flags.

## Data Providers

| Provider | Extra | API Key | Best for |
|----------|-------|---------|----------|
| Yahoo Finance | `yahoo` | No | Getting started, free data |
| Alpha Vantage | `alphavantage` | Yes (free tier) | Adjusted close, broad coverage |
| EODHD | `eodhd` | Yes | Global exchanges, exchange suffixes |
| Finnhub | `finnhub` | Yes (free tier) | US real-time data |
| Massive.com | `massive` | Yes | Professional-grade data |
| Interactive Brokers | `ibkr` | No (TWS/Gateway) | Real-time, existing IBKR users |

All providers are normalized to the same format. Switch with one config change — your watchlists, indicators, and signals work the same regardless of source.

## Architecture

Modular, with optional dependencies loaded lazily:

| Package | Purpose |
|---------|---------|
| `cli` | Click commands |
| `tui` | Textual terminal UI |
| `config` | TOML config + interactive wizard |
| `providers` | 6 data sources behind a common Protocol |
| `storage` | DuckDB persistence with delta-fetch |
| `indicators` | SMA, EMA, RSI, MACD, Bollinger |
| `analysis` | Rule-based entry signal engine |
| `output` | Rich tables + JSON envelope |

## Development

```bash
git clone https://github.com/fuchsblau/caracal.git
cd caracal
pip install -e ".[dev]"
pytest                # 466 tests, 86% coverage
ruff check .          # lint
ruff format .         # format
```

## Contributing

Contributions welcome. Open an issue first to discuss changes before submitting a PR.

## Disclaimer

**Caracal is not financial advice.** This tool is for informational and educational purposes only. It does not constitute investment advice, financial advice, trading advice, or any other sort of advice. Do not make financial decisions based solely on this tool's output. Trading involves risk, including losing your entire investment. Do your own research and consult a qualified financial advisor. The authors assume no responsibility for losses resulting from the use of this software.

## License

MIT — see [LICENSE](LICENSE).
