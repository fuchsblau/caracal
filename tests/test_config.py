"""Tests for caracal.config module."""

import pytest

from caracal.config import CaracalConfig, load_config


class TestCaracalConfigDefaults:
    def test_default_db_path(self):
        cfg = CaracalConfig()
        assert cfg.db_path == "~/.caracal/caracal.db"

    def test_default_period(self):
        cfg = CaracalConfig()
        assert cfg.default_period == "1y"

    def test_default_provider(self):
        cfg = CaracalConfig()
        assert cfg.default_provider == "yahoo"

    def test_default_format(self):
        cfg = CaracalConfig()
        assert cfg.default_format == "human"

    def test_frozen(self):
        cfg = CaracalConfig()
        with pytest.raises(AttributeError):
            cfg.db_path = "/other/path"


class TestLoadConfig:
    def test_load_defaults_when_no_file(self, tmp_path):
        cfg = load_config(tmp_path / "nonexistent.toml")
        assert cfg == CaracalConfig()

    def test_load_partial_config(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_period = "6mo"\n')
        cfg = load_config(config_file)
        assert cfg.default_period == "6mo"
        assert cfg.default_provider == "yahoo"

    def test_load_full_config(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'db_path = "/custom/db.duckdb"\n'
            'default_period = "3mo"\n'
            'default_provider = "yahoo"\n'
            'default_format = "json"\n'
        )
        cfg = load_config(config_file)
        assert cfg.db_path == "/custom/db.duckdb"
        assert cfg.default_period == "3mo"
        assert cfg.default_format == "json"

    def test_unknown_keys_ignored(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('future_key = "value"\ndefault_period = "6mo"\n')
        cfg = load_config(config_file)
        assert cfg.default_period == "6mo"

    def test_invalid_toml_raises(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("invalid = [unterminated\n")
        with pytest.raises(SystemExit):
            load_config(config_file)
