"""Tests for provider configuration in CaracalConfig."""

import os
from unittest.mock import patch

from caracal.config import CaracalConfig, load_config, mask_secret, write_config


class TestProviderConfig:
    def test_default_providers_empty(self):
        cfg = CaracalConfig()
        assert cfg.providers == {}

    def test_load_provider_section(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            'default_provider = "massive"\n\n'
            '[providers.massive]\n'
            'api_key = "pk_test123"\n'
        )
        cfg = load_config(config_file)
        assert cfg.providers == {"massive": {"api_key": "pk_test123"}}

    def test_load_multiple_provider_sections(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[providers.massive]\n'
            'api_key = "pk_test"\n\n'
            '[providers.ibkr]\n'
            'host = "127.0.0.1"\n'
            'port = "7497"\n'
            'client_id = "1"\n'
        )
        cfg = load_config(config_file)
        assert "massive" in cfg.providers
        assert "ibkr" in cfg.providers
        assert cfg.providers["ibkr"]["port"] == "7497"

    def test_no_provider_section_keeps_working(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_period = "6mo"\n')
        cfg = load_config(config_file)
        assert cfg.providers == {}
        assert cfg.default_period == "6mo"

    def test_env_var_override(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[providers.massive]\n'
            'api_key = "pk_from_file"\n'
        )
        with patch.dict(os.environ, {"CARACAL_MASSIVE_API_KEY": "pk_from_env"}):
            cfg = load_config(config_file)
        assert cfg.providers["massive"]["api_key"] == "pk_from_env"

    def test_env_var_creates_section(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_provider = "yahoo"\n')
        with patch.dict(os.environ, {"CARACAL_MASSIVE_API_KEY": "pk_env"}):
            cfg = load_config(config_file)
        assert cfg.providers["massive"]["api_key"] == "pk_env"

    def test_env_var_alphavantage(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_provider = "yahoo"\n')
        with patch.dict(os.environ, {"CARACAL_ALPHAVANTAGE_API_KEY": "av_key"}):
            cfg = load_config(config_file)
        assert cfg.providers["alphavantage"]["api_key"] == "av_key"

    def test_env_var_eodhd(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_provider = "yahoo"\n')
        with patch.dict(os.environ, {"CARACAL_EODHD_API_KEY": "eod_key"}):
            cfg = load_config(config_file)
        assert cfg.providers["eodhd"]["api_key"] == "eod_key"

    def test_env_var_finnhub(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_provider = "yahoo"\n')
        with patch.dict(os.environ, {"CARACAL_FINNHUB_API_KEY": "fh_key"}):
            cfg = load_config(config_file)
        assert cfg.providers["finnhub"]["api_key"] == "fh_key"

    def test_load_new_provider_sections(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            '[providers.alphavantage]\n'
            'api_key = "av_test"\n\n'
            '[providers.eodhd]\n'
            'api_key = "eod_test"\n'
            'default_exchange = "US"\n\n'
            '[providers.finnhub]\n'
            'api_key = "fh_test"\n'
        )
        cfg = load_config(config_file)
        assert cfg.providers["alphavantage"]["api_key"] == "av_test"
        assert cfg.providers["eodhd"]["default_exchange"] == "US"
        assert cfg.providers["finnhub"]["api_key"] == "fh_test"

    def test_frozen_providers_dict(self):
        cfg = CaracalConfig(providers={"massive": {"api_key": "test"}})
        assert cfg.providers["massive"]["api_key"] == "test"


class TestWriteConfigWithProviders:
    def test_roundtrip_with_providers(self, tmp_path):
        config_file = tmp_path / "config.toml"
        original = CaracalConfig(
            providers={"massive": {"api_key": "pk_test"}}
        )
        write_config(original, config_file)
        loaded = load_config(config_file)
        assert loaded.providers["massive"]["api_key"] == "pk_test"


class TestMaskSecret:
    def test_mask_short_key(self):
        assert mask_secret("abc") == "***"

    def test_mask_long_key(self):
        assert mask_secret("pk_abc123456") == "pk_a...***"

    def test_mask_empty(self):
        assert mask_secret("") == "***"
