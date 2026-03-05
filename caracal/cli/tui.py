"""caracal tui -- Launch interactive TUI."""

import click


def _launch_tui(config):
    """Import and launch TUI. Separated for testability."""
    from caracal.tui import CaracalApp

    app = CaracalApp(config=config)
    app.run()


@click.command()
@click.pass_context
def tui(ctx: click.Context) -> None:
    """Launch interactive TUI."""
    config = ctx.obj["config"]
    try:
        _launch_tui(config)
    except ImportError:
        click.echo(
            "Textual is not installed. "
            "Install with: pip install caracal-trading[tui]",
            err=True,
        )
        ctx.exit(1)
