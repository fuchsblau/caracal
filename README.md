# Caracal

```
░█▀▀░█▀█░█▀▄░█▀█░█▀▀░█▀█░█░░
░█░░░█▀█░█▀▄░█▀█░█░░░█▀█░█░░
░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀░▀░▀░▀▀▀
```

**Stock market analysis from your terminal — local, fast, automatable.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Caracal fetches market data, calculates technical indicators, and gives you entry point recommendations — all from the command line. Your data stays on your machine.

> **v1.2.0** — Multi-provider support. Fetch data from Yahoo Finance, Massive.com, or Interactive Brokers. All providers are optional — install only what you need.

## Disclaimer

**Caracal is not financial advice.** This tool is provided for informational and educational purposes only. It does not constitute investment advice, financial advice, trading advice, or any other sort of advice.

You should not make any financial decision based solely on the output of this tool. Trading stocks and other financial instruments involves risk, including the risk of losing your entire investment. Always do your own research and consult a qualified financial advisor before making investment decisions.

The authors and contributors of Caracal assume no responsibility for any losses or damages resulting from the use of this software.

## Features

- **Multiple data providers** — Yahoo Finance (default), Massive.com, Interactive Brokers. Install only what you need.
- **Fetch market data** — Pull OHLCV data with delta-fetch — only downloads what's new.
- **Technical indicators** — SMA, EMA, RSI, MACD, Bollinger Bands — calculated locally, no external service needed.
- **Entry signals** — Rule-based buy/sell/hold recommendations with confidence scoring to support your decisions.
- **Configurable** — TOML-based config with interactive wizard. Provider API keys, connection settings, and defaults.
- **Watchlists** — Create named watchlists, add/remove tickers, and view current prices with color-coded changes.
- **Built for automation** — Structured JSON output for piping into scripts, dashboards, or AI agents.

## Quickstart

```bash
pip install caracal-trading[all]
caracal init
caracal fetch AAPL
caracal analyze AAPL
caracal entry AAPL
```

## Example Output

```
$ caracal entry AAPL
AAPL: BUY (confidence: 72%)
  sma_20: 178.3400
  sma_50: 175.1200
  ema_12: 179.0500
  rsi_14: 38.2100
  macd: 1.2300
  macd_signal: 0.9800
  bollinger_upper: 185.4200
  bollinger_lower: 170.8600
```

```
$ caracal --format json entry AAPL
{"status": "ok", "data": {"signal": "buy", "confidence": 0.72, ...}, "meta": {"ticker": "AAPL"}}
```

## Usage

Fetch market data for a ticker:

```bash
caracal fetch AAPL
caracal fetch MSFT --period 2y
caracal fetch AAPL --provider massive
```

Run technical analysis:

```bash
caracal analyze AAPL
```

Get an entry point recommendation:

```bash
caracal entry AAPL
```

Use `--format json` for machine-readable output:

```bash
caracal --format json analyze AAPL
```

### Configuration

Initialize with defaults:

```bash
caracal init
```

Interactively change settings:

```bash
caracal configure
```

Config is stored in `~/.caracal/config.toml`:

```toml
db_path = "~/.caracal/caracal.db"
default_period = "1y"
default_provider = "yahoo"
default_format = "human"

[providers.massive]
api_key = "your-api-key"

[providers.ibkr]
host = "127.0.0.1"
port = "7497"
client_id = "1"
```

Provider settings can also be set via environment variables:

```bash
export CARACAL_MASSIVE_API_KEY="your-api-key"
```

CLI flags always override config values: `Defaults → config.toml → env vars → CLI flags`.

Use `--debug` to show full stack traces on errors:

```bash
caracal --debug fetch INVALID
```

### Watchlists

Create a watchlist and add tickers:

```bash
caracal watchlist create tech
caracal watchlist add tech AAPL MSFT GOOGL
```

View all your watchlists:

```bash
caracal watchlist list
```

Show current prices for a watchlist:

```bash
$ caracal watchlist show tech
        Watchlist — tech
┌────────┬────────┬────────┬─────────┐
│ Ticker │  Close │ Change │ Change% │
├────────┼────────┼────────┼─────────┤
│ AAPL   │ 178.72 │  +1.34 │  +0.76% │
│ GOOGL  │ 141.80 │  -0.45 │  -0.32% │
│ MSFT   │ 415.56 │  +2.10 │  +0.51% │
└────────┴────────┴────────┴─────────┘
```

Remove tickers or delete a watchlist:

```bash
caracal watchlist remove tech MSFT
caracal watchlist delete tech
```

## Requirements

- Python 3.12+

## Installation

Install with all providers:

```bash
pip install caracal-trading[all]
```

Or pick only the providers you need:

```bash
pip install caracal-trading[yahoo]     # Yahoo Finance (default, no API key needed)
pip install caracal-trading[massive]   # Massive.com (requires API key)
pip install caracal-trading[ibkr]      # Interactive Brokers (requires TWS/Gateway)
```

### Data Providers

| Provider | Package | Requires | Best for |
|----------|---------|----------|----------|
| Yahoo Finance | `caracal[yahoo]` | Nothing | Free data, getting started |
| Massive.com | `caracal[massive]` | API key | Professional market data |
| Interactive Brokers | `caracal[ibkr]` | TWS/Gateway running | Real-time data, existing IBKR account |

From source:

```bash
git clone https://github.com/fuchsblau/caracal.git
cd caracal
pip install -e ".[all]"
```

For development:

```bash
pip install -e ".[dev]"
```

## Development

```bash
# Run tests
pytest

# Lint
ruff check .

# Format
ruff format .
```

## Architecture

Caracal follows a modular architecture with six core packages:

| Package | Purpose |
|---------|---------|
| `cli` | Click-based command interface |
| `config` | TOML-based configuration management |
| `providers` | Market data source abstraction (Yahoo, Massive, IBKR) |
| `storage` | DuckDB-based local persistence |
| `indicators` | Technical indicator calculations |
| `analysis` | Rule-based entry signal logic |
| `output` | JSON and Rich table formatters |

## Contributing

Contributions are welcome. Please open an issue to discuss changes before submitting a pull request.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
