"""Caracal configuration management."""

from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass, fields
from pathlib import Path

import click

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


def load_config(path: Path | None = None) -> CaracalConfig:
    """Load configuration from TOML file, merged with defaults.

    Missing file returns defaults. Unknown keys are ignored.
    Invalid TOML syntax exits with an error message.
    """
    config_path = path or CONFIG_PATH
    if not config_path.exists():
        return CaracalConfig()

    try:
        raw = config_path.read_bytes()
        data = tomllib.loads(raw.decode())
    except tomllib.TOMLDecodeError as e:
        click.echo(
            click.style(f"Error: Invalid config file {config_path}: {e}", fg="red"),
            err=True,
        )
        sys.exit(1)

    valid_fields = {f.name for f in fields(CaracalConfig)}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return CaracalConfig(**filtered)
