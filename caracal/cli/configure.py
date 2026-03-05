"""caracal configure -- Interactively edit configuration."""

import click

from caracal.config import (
    CONFIG_DIR,
    CONFIG_PATH,
    CaracalConfig,
    load_config,
    mask_secret,
    write_config,
)
from caracal.output import human as human_out

# Provider settings: (key, prompt label, is_secret)
_PROVIDER_DISPLAY_NAMES = {
    "massive": "Massive",
    "ibkr": "IBKR",
}

_PROVIDER_SETTINGS = {
    "massive": [("api_key", "API key", True)],
    "ibkr": [
        ("host", "Host", False),
        ("port", "Port", False),
        ("client_id", "Client ID", False),
    ],
}

_PROVIDER_DEFAULTS = {
    "ibkr": {"host": "127.0.0.1", "port": "7497", "client_id": "1"},
}


@click.command()
@click.pass_context
def configure(ctx: click.Context) -> None:
    """Interactively configure caracal settings."""
    current = load_config()

    click.echo(human_out.format_logo())
    click.echo("Press Enter to keep current value.\n")

    db_path = click.prompt("  db_path", default=current.db_path)
    default_period = click.prompt("  default_period", default=current.default_period)
    default_provider = click.prompt(
        "  default_provider", default=current.default_provider
    )
    default_format = click.prompt("  default_format", default=current.default_format)

    # Provider-specific settings
    providers = dict(current.providers)
    for provider_name, settings in _PROVIDER_SETTINGS.items():
        display_name = _PROVIDER_DISPLAY_NAMES.get(provider_name, provider_name)
        if not click.confirm(
            f"\n  Configure {display_name} provider?",
            default=provider_name in providers,
        ):
            continue

        provider_cfg = dict(providers.get(provider_name, {}))
        defaults = _PROVIDER_DEFAULTS.get(provider_name, {})

        for key, label, is_secret in settings:
            existing = provider_cfg.get(key, defaults.get(key, ""))
            if is_secret and existing:
                display = mask_secret(existing)
                value = click.prompt(
                    f"    {label} (current: {display})",
                    default="",
                    show_default=False,
                )
                if not value:
                    value = existing
            else:
                value = click.prompt(f"    {label}", default=existing or "")
            if value:
                provider_cfg[key] = value
        providers[provider_name] = provider_cfg

    new_config = CaracalConfig(
        db_path=db_path,
        default_period=default_period,
        default_provider=default_provider,
        default_format=default_format,
        providers=providers,
    )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    path = write_config(new_config)
    path.chmod(0o600)
    click.echo(
        human_out.format_success_message(
            "Configuration saved.", {"Path": str(CONFIG_PATH)}
        )
    )
