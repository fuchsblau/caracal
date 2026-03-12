"""caracal daemon -- Background daemon management."""

from __future__ import annotations

import asyncio
import logging

import click

from caracal.config import CONFIG_DIR
from caracal.daemon.service import (
    DaemonAlreadyRunningError,
    DaemonNotRunningError,
    DaemonService,
)


@click.group()
def daemon():
    """Manage the Caracal background daemon."""
    pass


@daemon.command()
@click.pass_context
def start(ctx: click.Context) -> None:
    """Start the daemon in foreground."""
    config = ctx.obj["config"]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    service = DaemonService(config)
    try:
        asyncio.run(service.start())
    except DaemonAlreadyRunningError as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        ctx.exit(1)


@daemon.command()
@click.pass_context
def stop(ctx: click.Context) -> None:
    """Stop the running daemon."""
    try:
        DaemonService.stop()
        click.echo("Daemon stopped.")
    except DaemonNotRunningError as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        ctx.exit(1)


@daemon.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show daemon status."""
    config = ctx.obj["config"]
    info = DaemonService.get_status(config)

    if info["running"]:
        click.echo(f"Daemon running (PID {info['pid']})")
    else:
        click.echo("Daemon not running.")

    if info["recent_runs"]:
        click.echo("\nRecent task runs:")
        for run in info["recent_runs"]:
            status_icon = "ok" if run["status"] == "ok" else "FAIL"
            click.echo(
                f"  [{status_icon}] {run['task_name']} "
                f"at {run['started_at']} "
                f"({run['items_processed']} items)"
            )


@daemon.command("run-once")
@click.pass_context
def run_once(ctx: click.Context) -> None:
    """Run all daemon tasks once and exit."""
    config = ctx.obj["config"]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )
    service = DaemonService(config)
    results = asyncio.run(service.run_once())

    for result in results:
        status_str = click.style("ok", fg="green") if result.status == "ok" else click.style("FAIL", fg="red")
        click.echo(f"  {status_str}  {result.items_processed} items")
        if result.message:
            click.echo(f"       {result.message}")
