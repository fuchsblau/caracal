"""Caracal configuration management."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

import click

_KNOWN_PROVIDERS = {"yahoo", "massive", "ibkr", "alphavantage", "eodhd", "finnhub"}

CONFIG_DIR = Path.home() / ".caracal"
CONFIG_PATH = CONFIG_DIR / "config.toml"

VALID_FORMATS = {"human", "json"}
VALID_PERIODS = {"1y", "6mo", "3mo", "1mo", "5y"}


@dataclass(frozen=True)
class CaracalConfig:
    """Caracal configuration with sensible defaults."""

    db_path: str = "~/.caracal/caracal.db"
    default_period: str = "1y"
    default_provider: str = "yahoo"
    default_format: str = "human"
    providers: dict[str, dict[str, str]] = field(default_factory=dict)


CONFIG_TEMPLATE = """\
# Caracal configuration file
# See: https://github.com/fuchsblau/caracal

# Path to the DuckDB database file
db_path = "{db_path}"

# Default time period for data fetching (1y, 6mo, 3mo, 1mo, 5y)
default_period = "{default_period}"

# Default market data provider
default_provider = "{default_provider}"

# Default output format (human, json)
default_format = "{default_format}"

# Provider-specific configuration
# Uncomment and configure as needed:
#
# [providers.massive]
# api_key = "your-api-key"
#
# [providers.ibkr]
# host = "127.0.0.1"
# port = "7497"
# client_id = "1"
#
# [providers.alphavantage]
# api_key = "your-api-key"
#
# [providers.eodhd]
# api_key = "your-api-key"
# default_exchange = "US"
#
# [providers.finnhub]
# api_key = "your-api-key"
"""


def mask_secret(value: str) -> str:
    """Mask a secret value for display."""
    if len(value) <= 4:
        return "***"
    return f"{value[:4]}...***"


def _merge_env_vars(providers: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Merge CARACAL_<PROVIDER>_<KEY> env vars into provider config."""
    prefix = "CARACAL_"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue
        parts = key[len(prefix) :].lower().split("_", 1)
        if len(parts) != 2:
            continue
        provider_name, config_key = parts
        if provider_name not in _KNOWN_PROVIDERS:
            continue
        if provider_name not in providers:
            providers[provider_name] = {}
        providers[provider_name][config_key] = value
    return providers


def _toml_escape(value: str) -> str:
    """Escape a string for use in a TOML basic string."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def write_config(config: CaracalConfig, path: Path | None = None) -> Path:
    """Write configuration to TOML file.

    Returns the path written to.
    """
    config_path = path or CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = CONFIG_TEMPLATE.format(
        db_path=_toml_escape(config.db_path),
        default_period=_toml_escape(config.default_period),
        default_provider=_toml_escape(config.default_provider),
        default_format=_toml_escape(config.default_format),
    )
    # Append provider sections if present
    for provider_name, provider_config in config.providers.items():
        content += f"\n[providers.{provider_name}]\n"
        for k, v in provider_config.items():
            content += f'{k} = "{_toml_escape(v)}"\n'
    config_path.write_text(content)
    return config_path


def load_config(path: Path | None = None) -> CaracalConfig:
    """Load configuration from TOML file, merged with defaults.

    Missing file returns defaults. Unknown keys are ignored.
    Invalid TOML syntax exits with an error message.
    Environment variables CARACAL_<PROVIDER>_<KEY> override provider config.
    """
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        providers = _merge_env_vars({})
        return CaracalConfig(providers=providers)

    try:
        raw = config_path.read_bytes()
        data = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as e:
        click.echo(
            click.style(f"Error: Invalid config file {config_path}: {e}", fg="red"),
            err=True,
        )
        sys.exit(1)

    # Validate known constrained values before constructing config
    if "default_period" in data and data["default_period"] not in VALID_PERIODS:
        click.echo(
            click.style(
                f"Error: Invalid default_period '{data['default_period']}' "
                f"in {config_path}. Must be one of: {', '.join(sorted(VALID_PERIODS))}",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)

    if "default_format" in data and data["default_format"] not in VALID_FORMATS:
        click.echo(
            click.style(
                f"Error: Invalid default_format '{data['default_format']}' "
                f"in {config_path}. Must be one of: {', '.join(sorted(VALID_FORMATS))}",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)

    # Extract providers before filtering scalar fields
    providers = dict(data.pop("providers", {}))
    providers = _merge_env_vars(providers)

    valid_fields = {f.name for f in fields(CaracalConfig)} - {"providers"}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return CaracalConfig(providers=providers, **filtered)
