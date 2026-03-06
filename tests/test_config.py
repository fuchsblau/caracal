"""Tests for caracal.config module."""

import pytest

from caracal.config import CONFIG_TEMPLATE, CaracalConfig, load_config, write_config


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

    def test_load_config_warns_invalid_period(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_period = "invalid"\n')
        with pytest.raises(SystemExit):
            load_config(config_file)

    def test_load_config_warns_invalid_format(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_format = "xml"\n')
        with pytest.raises(SystemExit):
            load_config(config_file)

    def test_load_config_valid_period_accepted(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text('default_period = "6mo"\n')
        config = load_config(config_file)
        assert config.default_period == "6mo"


class TestConfigTemplate:
    def test_template_is_valid_toml(self):
        import tomllib

        parsed = tomllib.loads(CONFIG_TEMPLATE)
        assert "db_path" in parsed
        assert "default_period" in parsed
        assert "default_provider" in parsed
        assert "default_format" in parsed

    def test_template_has_comments(self):
        assert "#" in CONFIG_TEMPLATE


class TestWriteConfig:
    def test_write_creates_file(self, tmp_path):
        config_file = tmp_path / "config.toml"
        cfg = CaracalConfig()
        write_config(cfg, config_file)
        assert config_file.exists()

    def test_write_roundtrip(self, tmp_path):
        config_file = tmp_path / "config.toml"
        original = CaracalConfig(default_period="6mo", default_format="json")
        write_config(original, config_file)
        loaded = load_config(config_file)
        assert loaded == original

    def test_write_creates_parent_dirs(self, tmp_path):
        config_file = tmp_path / "subdir" / "config.toml"
        write_config(CaracalConfig(), config_file)
        assert config_file.exists()

    def test_write_roundtrip_with_backslashes(self, tmp_path):
        config_file = tmp_path / "config.toml"
        original = CaracalConfig(db_path="C:\\Users\\test\\caracal.db")
        write_config(original, config_file)
        loaded = load_config(config_file)
        assert loaded == original

    def test_write_roundtrip_with_quotes(self, tmp_path):
        config_file = tmp_path / "config.toml"
        original = CaracalConfig(db_path='/path/with "quotes"/db')
        write_config(original, config_file)
        loaded = load_config(config_file)
        assert loaded == original
