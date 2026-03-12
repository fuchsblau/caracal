"""Caracal CLI entry point."""

import click

from caracal import __version__
from caracal.config import ConfigError, load_config
from caracal.output.human import LOGO


class CaracalGroup(click.Group):
    """Custom group that prepends the ASCII logo to help output."""

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        formatter.write(f"\n{LOGO}\n\n")
        super().format_help(ctx, formatter)


@click.group(cls=CaracalGroup)
@click.version_option(version=__version__, prog_name="caracal")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"]),
    default=None,
    help="Output format.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Show full stack traces on error.",
)
@click.pass_context
def cli(ctx: click.Context, output_format: str | None, debug: bool) -> None:
    """Automated stock analysis from your terminal."""
    ctx.ensure_object(dict)
    try:
        config = load_config()
    except ConfigError as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        ctx.exit(1)
        return
    ctx.obj["config"] = config
    ctx.obj["format"] = output_format or config.default_format
    ctx.obj["debug"] = debug


from caracal.cli.fetch import fetch  # noqa: E402

cli.add_command(fetch)

from caracal.cli.analyze import analyze  # noqa: E402

cli.add_command(analyze)

from caracal.cli.entry import entry  # noqa: E402

cli.add_command(entry)

from caracal.cli.init import init  # noqa: E402

cli.add_command(init)

from caracal.cli.configure import configure  # noqa: E402

cli.add_command(configure)

from caracal.cli.watchlist import watchlist  # noqa: E402

cli.add_command(watchlist)

from caracal.cli.tui import tui  # noqa: E402

cli.add_command(tui)

from caracal.cli.daemon_cmd import daemon  # noqa: E402

cli.add_command(daemon)
