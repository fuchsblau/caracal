"""caracal init -- Initialize caracal configuration."""

from pathlib import Path

import click

CONFIG_DIR = Path.home() / ".caracal"


@click.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize caracal configuration directory."""
    output_format = ctx.obj["format"]

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    db_path = CONFIG_DIR / "caracal.db"

    if output_format == "json":
        from caracal.output import json as json_out

        click.echo(
            json_out.format_success(
                {
                    "config_dir": str(CONFIG_DIR),
                    "db_path": str(db_path),
                    "message": "Caracal initialized successfully.",
                },
                {"command": "init"},
            )
        )
    else:
        click.echo("Caracal initialized.")
        click.echo(f"  Config directory: {CONFIG_DIR}")
        click.echo(f"  Database: {db_path}")
