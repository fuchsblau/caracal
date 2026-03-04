"""caracal configure -- Interactively edit configuration."""

import click

from caracal.config import (
    CONFIG_DIR,
    CONFIG_PATH,
    CaracalConfig,
    load_config,
    write_config,
)
from caracal.output import human as human_out


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

    new_config = CaracalConfig(
        db_path=db_path,
        default_period=default_period,
        default_provider=default_provider,
        default_format=default_format,
    )

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    write_config(new_config)
    click.echo(
        human_out.format_success_message(
            "Configuration saved.", {"Path": str(CONFIG_PATH)}
        )
    )
