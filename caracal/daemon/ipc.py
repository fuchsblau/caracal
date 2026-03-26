"""Unix socket IPC server for daemon-TUI communication.

Implements a JSON-Lines protocol (newline-delimited JSON) over a Unix domain socket.
Supports multiple simultaneous client connections with subscribe/command/query messages.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from caracal.daemon.registry import TaskContext

logger = logging.getLogger("caracal.daemon.ipc")


class IPCServer:
    """Unix socket IPC server for daemon-TUI communication.

    Clients connect and send JSON-Lines messages. Subscribed clients
    receive all broadcast events (task_complete, data_update, error).
    """

    def __init__(
        self,
        socket_path: Path,
        context: TaskContext,
        run_tasks_callback: Callable[[], Awaitable[None]] | None = None,
        refresh_cooldown_seconds: int = 60,
    ) -> None:
        self._socket_path = socket_path
        self._context = context
        self._clients: set[asyncio.StreamWriter] = set()
        self._server: asyncio.Server | None = None
        self._run_tasks_callback = run_tasks_callback
        self._refresh_cooldown = refresh_cooldown_seconds
        self._last_refresh_time: float = 0.0
        self._refresh_task: asyncio.Task | None = None
        self._command_handlers: dict[str, Callable[..., Awaitable[dict]]] = {
            "refresh": self._handle_refresh,
            "create_watchlist": self._handle_create_watchlist,
            "add_ticker": self._handle_add_ticker,
            "status": self._handle_status,
        }

    async def start(self) -> None:
        """Start the Unix socket server. Remove stale socket file first."""
        self._socket_path.parent.mkdir(parents=True, exist_ok=True)
        self._socket_path.unlink(missing_ok=True)
        self._server = await asyncio.start_unix_server(
            self._handle_client, path=str(self._socket_path)
        )
        logger.info("IPC server listening on %s", self._socket_path)

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a single client connection."""
        logger.debug("New IPC client connected")
        try:
            while True:
                line = await reader.readline()
                if not line:
                    # Client disconnected (EOF)
                    break
                try:
                    message = json.loads(line.decode("utf-8").strip())
                except (json.JSONDecodeError, UnicodeDecodeError):
                    await self._send(
                        writer,
                        {"type": "error", "msg": "Invalid JSON"},
                    )
                    continue

                await self._dispatch(message, writer)
        except ConnectionResetError:
            logger.debug("IPC client connection reset")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected error handling IPC client")
        finally:
            self._clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
            logger.debug("IPC client disconnected")

    async def _dispatch(self, message: dict, writer: asyncio.StreamWriter) -> None:
        """Dispatch an incoming message to the appropriate handler."""
        msg_type = message.get("type")

        if msg_type == "subscribe":
            self._clients.add(writer)
            await self._send(
                writer, {"type": "result", "cmd": "subscribe", "status": "ok"}
            )
            logger.debug("Client subscribed (total: %d)", len(self._clients))

        elif msg_type == "command":
            cmd = message.get("cmd")
            handler = self._command_handlers.get(cmd) if cmd else None
            if handler is None:
                await self._send(
                    writer,
                    {"type": "error", "msg": f"Unknown command: {cmd}"},
                )
                return
            result = await handler(message)
            await self._send(writer, result)

        elif msg_type == "query":
            cmd = message.get("cmd")
            handler = self._command_handlers.get(cmd) if cmd else None
            if handler is None:
                await self._send(
                    writer,
                    {"type": "error", "msg": f"Unknown query: {cmd}"},
                )
                return
            result = await handler(message)
            await self._send(writer, result)

        else:
            await self._send(
                writer,
                {"type": "error", "msg": f"Unknown message type: {msg_type}"},
            )

    async def broadcast(self, message: dict) -> None:
        """Send a JSON-Line message to all subscribed clients."""
        if not self._clients:
            return
        data = json.dumps(message).encode("utf-8") + b"\n"
        dead_clients: list[asyncio.StreamWriter] = []
        for writer in list(self._clients):
            try:
                writer.write(data)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError, OSError):
                dead_clients.append(writer)
            except Exception:
                dead_clients.append(writer)
        for writer in dead_clients:
            self._clients.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    async def shutdown(self) -> None:
        """Graceful shutdown: notify clients, close socket, clean up."""
        logger.info("Shutting down IPC server")
        # Notify all subscribed clients
        await self.broadcast({"type": "shutdown"})

        # Close all client writers
        for writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

        # Close the server
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        # Remove socket file
        self._socket_path.unlink(missing_ok=True)
        logger.info("IPC server stopped")

    @property
    def client_count(self) -> int:
        """Number of currently subscribed clients."""
        return len(self._clients)

    # -- Command handlers ---

    async def _handle_refresh(self, message: dict) -> dict:
        """Handle refresh command: trigger immediate data fetch.

        Rate-limited: rejects if a refresh is already running or if the
        cooldown period has not elapsed since the last refresh.
        """
        # Guard: concurrent execution
        if self._refresh_task is not None and not self._refresh_task.done():
            return {
                "type": "error",
                "cmd": "refresh",
                "msg": "Refresh already running",
            }

        # Guard: cooldown period
        now = time.monotonic()
        elapsed = now - self._last_refresh_time
        if self._last_refresh_time > 0 and elapsed < self._refresh_cooldown:
            remaining = int(self._refresh_cooldown - elapsed)
            return {
                "type": "error",
                "cmd": "refresh",
                "msg": f"Refresh cooldown: {remaining}s remaining",
            }

        if self._run_tasks_callback is not None:
            try:
                self._last_refresh_time = time.monotonic()
                self._refresh_task = asyncio.create_task(
                    self._run_tasks_callback()
                )
                return {"type": "result", "cmd": "refresh", "status": "ok"}
            except Exception:
                logger.exception("Failed to trigger refresh")
                return {"type": "error", "cmd": "refresh", "msg": "Failed to trigger refresh"}
        return {"type": "result", "cmd": "refresh", "status": "ok"}

    async def _handle_create_watchlist(self, message: dict) -> dict:
        """Handle create_watchlist command."""
        name = message.get("name")
        if not name:
            return {
                "type": "error",
                "cmd": "create_watchlist",
                "msg": "Missing 'name' parameter",
            }
        try:
            self._context.db.create_watchlist(name)
            return {
                "type": "result",
                "cmd": "create_watchlist",
                "status": "ok",
                "name": name,
            }
        except Exception:
            logger.exception("Failed to create watchlist")
            return {
                "type": "error",
                "cmd": "create_watchlist",
                "msg": "Failed to create watchlist",
            }

    async def _handle_add_ticker(self, message: dict) -> dict:
        """Handle add_ticker command."""
        watchlist = message.get("watchlist")
        tickers = message.get("tickers", [])
        if not watchlist:
            return {
                "type": "error",
                "cmd": "add_ticker",
                "msg": "Missing 'watchlist' parameter",
            }
        if not tickers:
            return {
                "type": "error",
                "cmd": "add_ticker",
                "msg": "Missing 'tickers' parameter",
            }
        try:
            for ticker in tickers:
                self._context.db.add_to_watchlist(watchlist, ticker)
            return {
                "type": "result",
                "cmd": "add_ticker",
                "status": "ok",
                "watchlist": watchlist,
                "tickers": tickers,
            }
        except Exception:
            logger.exception("Failed to add ticker")
            return {
                "type": "error",
                "cmd": "add_ticker",
                "msg": "Failed to add ticker",
            }

    async def _handle_status(self, message: dict) -> dict:
        """Handle status query."""
        try:
            recent_runs = self._context.db.get_recent_worker_runs(limit=10)
            return {
                "type": "status",
                "clients": self.client_count,
                "recent_runs": recent_runs,
            }
        except Exception:
            logger.exception("Failed to get status")
            return {
                "type": "error",
                "cmd": "status",
                "msg": "Failed to get status",
            }

    # -- Helper ---

    @staticmethod
    async def _send(writer: asyncio.StreamWriter, message: dict) -> None:
        """Send a single JSON-Line message to a writer."""
        data = json.dumps(message).encode("utf-8") + b"\n"
        writer.write(data)
        await writer.drain()
