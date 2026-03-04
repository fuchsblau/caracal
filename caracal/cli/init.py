"""caracal init -- Initialize caracal configuration."""

import click

from caracal.config import CONFIG_DIR, CONFIG_PATH, CaracalConfig, write_config


@click.command()
@click.option("--force", is_flag=True, default=False, help="Overwrite existing config.")
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Initialize caracal configuration directory and config file."""
    output_format = ctx.obj["format"]

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_PATH.exists() and not force:
        if output_format == "json":
            from caracal.output import json as json_out

            click.echo(
                json_out.format_success(
                    {
                        "config_dir": str(CONFIG_DIR),
                        "config_file": str(CONFIG_PATH),
                        "message": "Config already exists. Use --force to overwrite.",
                    },
                    {"command": "init"},
                )
            )
        else:
            click.echo(f"Config already exists: {CONFIG_PATH}")
            click.echo("Use 'caracal init --force' to overwrite.")
        return

    config = CaracalConfig()
    write_config(config)

    if output_format == "json":
        from caracal.output import json as json_out

        click.echo(
            json_out.format_success(
                {
                    "config_dir": str(CONFIG_DIR),
                    "config_file": str(CONFIG_PATH),
                    "message": "Caracal initialized successfully.",
                },
                {"command": "init"},
            )
        )
    else:
        click.echo("Caracal initialized.")
        click.echo(f"  Config: {CONFIG_PATH}")
        click.echo(f"  Database: {config.db_path}")
