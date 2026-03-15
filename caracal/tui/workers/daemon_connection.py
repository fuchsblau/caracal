"""Daemon connection worker for TUI-daemon IPC communication.

Connects to the daemon's Unix socket, subscribes for broadcasts,
and forwards events to the Textual app via messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from textual.message import Message

from caracal.config import CONFIG_DIR

logger = logging.getLogger("caracal.tui.daemon")

SOCKET_PATH = CONFIG_DIR / "caracal.sock"


class DaemonConnected(Message):
    """Successfully connected to daemon."""


class DaemonDisconnected(Message):
    """Daemon connection lost or not available."""


class DaemonEvent(Message):
    """Event received from daemon via IPC."""

    def __init__(self, data: dict) -> None:
        self.data = data
        super().__init__()


async def daemon_connect(
    socket_path: Path | None = None,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Open a Unix socket connection to the daemon.

    Returns the (reader, writer) pair.
    Raises ConnectionRefusedError or FileNotFoundError if the daemon is not running.
    """
    path = socket_path or SOCKET_PATH
    return await asyncio.open_unix_connection(str(path))


async def send_ipc_message(writer: asyncio.StreamWriter, message: dict) -> None:
    """Send a JSON-Lines message over the IPC connection."""
    data = json.dumps(message).encode("utf-8") + b"\n"
    writer.write(data)
    await writer.drain()


async def recv_ipc_message(reader: asyncio.StreamReader, timeout: float = 5.0) -> dict:
    """Read a single JSON-Lines message from the IPC connection."""
    line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    if not line:
        raise ConnectionError("Connection closed by daemon")
    return json.loads(line.decode("utf-8").strip())
