"""Caracal CLI entry point."""

import click

from caracal import __version__


@click.group()
@click.version_option(version=__version__, prog_name="caracal")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"]),
    default="human",
    help="Output format.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Show full stack traces on error.",
)
@click.pass_context
def cli(ctx: click.Context, output_format: str, debug: bool) -> None:
    """Caracal – Automated stock analysis."""
    ctx.ensure_object(dict)
    ctx.obj["format"] = output_format
    ctx.obj["debug"] = debug


from caracal.cli.fetch import fetch  # noqa: E402

cli.add_command(fetch)

from caracal.cli.analyze import analyze  # noqa: E402

cli.add_command(analyze)

from caracal.cli.entry import entry  # noqa: E402

cli.add_command(entry)

from caracal.cli.init import init  # noqa: E402

cli.add_command(init)
