# Caracal

```
░█▀▀░█▀█░█▀▄░█▀█░█▀▀░█▀█░█░░
░█░░░█▀█░█▀▄░█▀█░█░░░█▀█░█░░
░▀▀▀░▀░▀░▀░▀░▀░▀░▀▀▀░▀░▀░▀▀▀
```

**Stock market analysis from your terminal — local, fast, automatable.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Caracal fetches market data, calculates technical indicators, and gives you entry point recommendations — all from the command line. Your data stays on your machine, no account or API key required.

> **v1.1.0** — Watchlist management. Create watchlists, track tickers, and view live prices — all from the CLI.

## Disclaimer

**Caracal is not financial advice.** This tool is provided for informational and educational purposes only. It does not constitute investment advice, financial advice, trading advice, or any other sort of advice.

You should not make any financial decision based solely on the output of this tool. Trading stocks and other financial instruments involves risk, including the risk of losing your entire investment. Always do your own research and consult a qualified financial advisor before making investment decisions.

The authors and contributors of Caracal assume no responsibility for any losses or damages resulting from the use of this software.

## Features

- **Fetch market data** — Pull OHLCV data from Yahoo Finance. Delta-fetch ensures you only download what's new.
- **Technical indicators** — SMA, EMA, RSI, MACD, Bollinger Bands — calculated locally, no external service needed.
- **Entry signals** — Rule-based buy/sell/hold recommendations with confidence scoring to support your decisions.
- **Configurable** — TOML-based config with interactive wizard. Set your defaults once, override per command.
- **Watchlists** — Create named watchlists, add/remove tickers, and view current prices with color-coded changes.
- **Built for automation** — Structured JSON output for piping into scripts, dashboards, or AI agents.

## Quickstart

```bash
pip install -e "."
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
```

CLI flags always override config values: `Defaults → config.toml → CLI flags`.

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

```bash
git clone https://github.com/fuchsblau/caracal.git
cd caracal
pip install -e "."
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
| `providers` | Market data source abstraction (Yahoo Finance) |
| `storage` | DuckDB-based local persistence |
| `indicators` | Technical indicator calculations |
| `analysis` | Rule-based entry signal logic |
| `output` | JSON and Rich table formatters |

## Contributing

Contributions are welcome. Please open an issue to discuss changes before submitting a pull request.

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
