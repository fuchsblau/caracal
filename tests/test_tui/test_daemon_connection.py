"""Tests for TUI daemon connection (US-089).

Tests the DaemonConnection worker, auto-reconnect, footer status display,
and connected/disconnected CRUD mode switching.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from caracal.config import CaracalConfig
from caracal.storage.duckdb import DuckDBStorage
from caracal.tui import CaracalApp
from caracal.tui.data import DataService
from caracal.tui.widgets.footer import CaracalFooter
from caracal.tui.workers.daemon_connection import (
    DaemonConnected,
    DaemonDisconnected,
    DaemonEvent,
    daemon_connect,
    recv_ipc_message,
    send_ipc_message,
)

# -- Helpers ------------------------------------------------------------------


def _make_app(
    config: CaracalConfig,
    socket_path: Path | None = None,
) -> CaracalApp:
    """Build a CaracalApp with in-memory storage and optional socket path."""
    storage = DuckDBStorage(":memory:")
    data_service = DataService(config, storage=storage)
    return CaracalApp(
        config=config,
        data_service=data_service,
        socket_path=socket_path,
    )


def _make_app_with_watchlists(
    config: CaracalConfig,
    watchlists: dict[str, list[str]] | None = None,
    socket_path: Path | None = None,
) -> CaracalApp:
    """Build a CaracalApp with pre-populated watchlists."""
    from datetime import date, timedelta

    import pandas as pd

    if watchlists is None:
        watchlists = {"tech": ["AAPL"]}
    storage = DuckDBStorage(":memory:")
    for name, tickers in watchlists.items():
        storage.create_watchlist(name)
        for ticker in tickers:
            storage.add_to_watchlist(name, ticker)
            rows = []
            for i in range(31):
                d = date.today() - timedelta(days=30 - i)
                rows.append(
                    {
                        "date": d,
                        "open": 150.0 + i * 0.1,
                        "high": 152.0 + i * 0.1,
                        "low": 149.0 + i * 0.1,
                        "close": 151.0 + i * 0.1,
                        "volume": 1_000_000,
                    }
                )
            storage.store_ohlcv(ticker, pd.DataFrame(rows))
    data_service = DataService(config, storage=storage)
    return CaracalApp(
        config=config,
        data_service=data_service,
        socket_path=socket_path,
    )


# -- Fixtures -----------------------------------------------------------------


@pytest.fixture
def config():
    return CaracalConfig(db_path=":memory:")


@pytest.fixture
def socket_path(tmp_path):
    return tmp_path / "test.sock"


# -- Message classes ----------------------------------------------------------


class TestMessageClasses:
    def test_daemon_connected_is_message(self):
        msg = DaemonConnected()
        assert msg is not None

    def test_daemon_disconnected_is_message(self):
        msg = DaemonDisconnected()
        assert msg is not None

    def test_daemon_event_has_data(self):
        data = {"type": "task_complete", "task": "news", "items": 5}
        msg = DaemonEvent(data)
        assert msg.data == data

    def test_daemon_event_preserves_data(self):
        data = {"type": "data_update", "table": "quotes"}
        msg = DaemonEvent(data)
        assert msg.data["type"] == "data_update"
        assert msg.data["table"] == "quotes"


# -- IPC helper functions -----------------------------------------------------


class TestIPCHelpers:
    @pytest.mark.asyncio
    async def test_send_ipc_message(self):
        """send_ipc_message writes JSON-Lines to the writer."""
        writer = MagicMock()
        writer.drain = AsyncMock()
        await send_ipc_message(writer, {"type": "subscribe"})
        writer.write.assert_called_once()
        written = writer.write.call_args[0][0]
        assert written.endswith(b"\n")
        parsed = json.loads(written.decode("utf-8").strip())
        assert parsed == {"type": "subscribe"}

    @pytest.mark.asyncio
    async def test_recv_ipc_message(self):
        """recv_ipc_message reads a JSON-Lines message from reader."""
        reader = AsyncMock()
        msg = {"type": "result", "status": "ok"}
        reader.readline = AsyncMock(
            return_value=json.dumps(msg).encode("utf-8") + b"\n"
        )
        result = await recv_ipc_message(reader, timeout=1.0)
        assert result == msg

    @pytest.mark.asyncio
    async def test_recv_ipc_message_empty_line_raises(self):
        """recv_ipc_message raises ConnectionError on empty line (EOF)."""
        reader = AsyncMock()
        reader.readline = AsyncMock(return_value=b"")
        with pytest.raises(ConnectionError):
            await recv_ipc_message(reader, timeout=1.0)

    @pytest.mark.asyncio
    async def test_daemon_connect_file_not_found(self, tmp_path):
        """daemon_connect raises FileNotFoundError for nonexistent socket."""
        with pytest.raises((FileNotFoundError, ConnectionRefusedError)):
            await daemon_connect(tmp_path / "nonexistent.sock")


# -- Footer daemon status ----------------------------------------------------


class TestFooterDaemonStatus:
    @pytest.mark.asyncio
    async def test_default_status_is_disconnected(self, config):
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            assert footer.daemon_status == "\u25cb Disconnected"

    @pytest.mark.asyncio
    async def test_daemon_status_is_reactive(self):
        """daemon_status must be a reactive property."""
        from textual.reactive import reactive

        assert isinstance(CaracalFooter.__dict__["daemon_status"], reactive), (
            "daemon_status should be a Textual reactive"
        )

    @pytest.mark.asyncio
    async def test_daemon_status_label_present(self, config):
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            label = footer.query_one("#daemon-status")
            assert label is not None

    @pytest.mark.asyncio
    async def test_daemon_status_updates_label(self, config):
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            footer = app.query_one(CaracalFooter)
            footer.daemon_status = "\u25cf Connected"
            label = footer.query_one("#daemon-status")
            assert "\u25cf Connected" in label.content


# -- App daemon connection reactive -------------------------------------------


class TestAppDaemonReactive:
    @pytest.mark.asyncio
    async def test_daemon_connected_default_false(self, config):
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            assert app.daemon_connected is False

    @pytest.mark.asyncio
    async def test_daemon_connected_is_reactive(self):
        from textual.reactive import reactive

        assert isinstance(CaracalApp.__dict__["daemon_connected"], reactive), (
            "daemon_connected should be a Textual reactive"
        )


# -- Daemon worker behavior ---------------------------------------------------


class TestDaemonWorkerBehavior:
    @pytest.mark.asyncio
    async def test_worker_posts_connected_on_success(self, config):
        """Worker posts DaemonConnected after successful subscribe."""
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))

        # Simulate the worker's behavior directly via message handlers
        async with app.run_test():
            assert app.daemon_connected is False
            # Simulate what the worker does on successful connection
            app.post_message(DaemonConnected())
            await asyncio.sleep(0.1)
            assert app.daemon_connected is True
            footer = app.query_one(CaracalFooter)
            assert "\u25cf Connected" in footer.daemon_status

    @pytest.mark.asyncio
    async def test_worker_posts_disconnected_on_no_socket(self, config):
        """Worker posts DaemonDisconnected when socket does not exist."""
        app = _make_app(config, socket_path=Path("/nonexistent/caracal.sock"))
        async with app.run_test():
            # Give the worker time to attempt connection and fail
            await asyncio.sleep(0.5)
            assert app.daemon_connected is False
            footer = app.query_one(CaracalFooter)
            assert "\u25cb Disconnected" in footer.daemon_status

    @pytest.mark.asyncio
    async def test_worker_forwards_events_via_messages(self, config):
        """DaemonEvent messages are handled by the app."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            with patch.object(app, "_load_news") as mock_load:
                # Simulate receiving a daemon event
                app.post_message(
                    DaemonEvent(
                        {
                            "type": "task_complete",
                            "task": "news",
                            "items": 12,
                        }
                    )
                )
                await asyncio.sleep(0.1)
                mock_load.assert_called()

    @pytest.mark.asyncio
    async def test_worker_handles_connection_loss(self, config):
        """DaemonDisconnected resets status after connection loss."""
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            # First, simulate connected state
            app.daemon_connected = True
            footer = app.query_one(CaracalFooter)
            footer.daemon_status = "\u25cf Connected"

            # Simulate disconnection
            app.post_message(DaemonDisconnected())
            await asyncio.sleep(0.1)

            assert app.daemon_connected is False
            assert "\u25cb Disconnected" in footer.daemon_status

    @pytest.mark.asyncio
    async def test_daemon_worker_function_connect_failure(self):
        """_daemon_worker handles connection errors gracefully."""
        from caracal.tui.workers.daemon_connection import (
            daemon_connect,
        )

        # Test that daemon_connect raises on missing socket
        with pytest.raises((FileNotFoundError, ConnectionRefusedError, OSError)):
            await daemon_connect(Path("/nonexistent/sock"))

    @pytest.mark.asyncio
    async def test_daemon_worker_subscribe_flow(self, socket_path):
        """Full subscribe flow works with real socket."""
        # Start a test server
        server = await asyncio.start_unix_server(
            lambda r, w: _echo_subscribe(r, w),
            path=str(socket_path),
        )

        reader, writer = await daemon_connect(socket_path)
        await send_ipc_message(writer, {"type": "subscribe"})
        response = await recv_ipc_message(reader, timeout=2.0)

        assert response["type"] == "result"
        assert response["status"] == "ok"

        writer.close()
        await writer.wait_closed()
        server.close()
        await server.wait_closed()


async def _echo_subscribe(reader, writer):
    """Simple test server that responds to subscribe."""
    line = await reader.readline()
    if line:
        msg = json.loads(line.decode("utf-8").strip())
        if msg.get("type") == "subscribe":
            response = (
                json.dumps(
                    {
                        "type": "result",
                        "cmd": "subscribe",
                        "status": "ok",
                    }
                ).encode("utf-8")
                + b"\n"
            )
            writer.write(response)
            await writer.drain()
    writer.close()
    await writer.wait_closed()


# -- App event handlers -------------------------------------------------------


class TestAppEventHandlers:
    @pytest.mark.asyncio
    async def test_on_daemon_connected_sets_status(self, config):
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            app.on_daemon_connected(DaemonConnected())
            assert app.daemon_connected is True
            footer = app.query_one(CaracalFooter)
            assert "\u25cf Connected" in footer.daemon_status

    @pytest.mark.asyncio
    async def test_on_daemon_disconnected_sets_status(self, config):
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            # First set to connected
            app.daemon_connected = True
            # Then disconnect
            app.on_daemon_disconnected(DaemonDisconnected())
            assert app.daemon_connected is False
            footer = app.query_one(CaracalFooter)
            assert "\u25cb Disconnected" in footer.daemon_status

    @pytest.mark.asyncio
    async def test_on_daemon_event_task_complete_news(self, config):
        """task_complete event for news triggers news reload."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            with patch.object(app, "_load_news") as mock_load:
                event = DaemonEvent(
                    {"type": "task_complete", "task": "news", "items": 5}
                )
                app.on_daemon_event(event)
                mock_load.assert_called()

    @pytest.mark.asyncio
    async def test_on_daemon_event_task_complete_fetch(self, config):
        """task_complete event for fetch triggers data refresh."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            with patch.object(app, "_refresh_visible_data") as mock_refresh:
                event = DaemonEvent(
                    {"type": "task_complete", "task": "fetch", "items": 42}
                )
                app.on_daemon_event(event)
                mock_refresh.assert_called()

    @pytest.mark.asyncio
    async def test_on_daemon_event_data_update(self, config):
        """data_update event triggers data refresh."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            with patch.object(app, "_refresh_visible_data") as mock_refresh:
                event = DaemonEvent({"type": "data_update", "table": "quotes"})
                app.on_daemon_event(event)
                mock_refresh.assert_called()

    @pytest.mark.asyncio
    async def test_on_daemon_event_shutdown(self, config):
        """shutdown event switches to disconnected mode."""
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            app.daemon_connected = True
            event = DaemonEvent({"type": "shutdown"})
            app.on_daemon_event(event)
            assert app.daemon_connected is False
            footer = app.query_one(CaracalFooter)
            assert "\u25cb Disconnected" in footer.daemon_status


# -- Connected-mode CRUD (IPC commands) ---------------------------------------


class TestConnectedModeCRUD:
    @pytest.mark.asyncio
    async def test_create_watchlist_sends_ipc_when_connected(self, config):
        """In connected mode, create_watchlist sends IPC command."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            app.daemon_connected = True
            mock_writer = MagicMock()
            mock_writer.drain = AsyncMock()
            app._daemon_writer = mock_writer

            with patch.object(
                app, "_send_ipc_command", new_callable=AsyncMock
            ) as mock_send:
                await app._on_create_result("newlist")
                mock_send.assert_called_once()
                cmd = mock_send.call_args[0][0]
                assert cmd["type"] == "command"
                assert cmd["cmd"] == "create_watchlist"
                assert cmd["name"] == "newlist"

    @pytest.mark.asyncio
    async def test_create_watchlist_uses_db_when_disconnected(self, config):
        """In disconnected mode, create_watchlist writes directly to DB."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            assert app.daemon_connected is False
            await app._on_create_result("newlist")
            assert "newlist" in app._watchlist_names

    @pytest.mark.asyncio
    async def test_delete_watchlist_sends_ipc_when_connected(self, config):
        """In connected mode, delete_watchlist sends IPC command."""
        app = _make_app_with_watchlists(
            config,
            watchlists={"tech": ["AAPL"]},
            socket_path=Path("/nonexistent/path.sock"),
        )
        async with app.run_test():
            app.daemon_connected = True
            mock_writer = MagicMock()
            mock_writer.drain = AsyncMock()
            app._daemon_writer = mock_writer

            with patch.object(
                app, "_send_ipc_command", new_callable=AsyncMock
            ) as mock_send:
                await app._on_delete_result(True)
                mock_send.assert_called_once()
                cmd = mock_send.call_args[0][0]
                assert cmd["cmd"] == "delete_watchlist"

    @pytest.mark.asyncio
    async def test_add_ticker_sends_ipc_when_connected(self, config):
        """In connected mode, add_ticker sends IPC command."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            app.daemon_connected = True
            mock_writer = MagicMock()
            mock_writer.drain = AsyncMock()
            app._daemon_writer = mock_writer

            with patch.object(
                app, "_send_ipc_command", new_callable=AsyncMock
            ) as mock_send:
                await app._on_add_result(["NVDA"])
                mock_send.assert_called_once()
                cmd = mock_send.call_args[0][0]
                assert cmd["cmd"] == "add_ticker"
                assert cmd["tickers"] == ["NVDA"]

    @pytest.mark.asyncio
    async def test_remove_ticker_sends_ipc_when_connected(self, config):
        """In connected mode, remove_ticker sends IPC command."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            app.daemon_connected = True
            mock_writer = MagicMock()
            mock_writer.drain = AsyncMock()
            app._daemon_writer = mock_writer
            app._pending_remove_ticker = "AAPL"

            with patch.object(
                app, "_send_ipc_command", new_callable=AsyncMock
            ) as mock_send:
                await app._on_remove_result(True)
                mock_send.assert_called_once()
                cmd = mock_send.call_args[0][0]
                assert cmd["cmd"] == "remove_ticker"
                assert cmd["ticker"] == "AAPL"

    @pytest.mark.asyncio
    async def test_refresh_sends_ipc_when_connected(self, config):
        """In connected mode, refresh sends IPC command instead of direct fetch."""
        app = _make_app_with_watchlists(
            config, socket_path=Path("/nonexistent/path.sock")
        )
        async with app.run_test():
            app.daemon_connected = True
            mock_writer = MagicMock()
            mock_writer.drain = AsyncMock()
            app._daemon_writer = mock_writer

            with patch.object(
                app, "_send_ipc_command", new_callable=AsyncMock
            ) as mock_send:
                await app._do_live_refresh()
                mock_send.assert_called_once()
                cmd = mock_send.call_args[0][0]
                assert cmd["cmd"] == "refresh"


# -- Disconnected-mode CRUD (direct DB) --------------------------------------


class TestDisconnectedModeCRUD:
    @pytest.mark.asyncio
    async def test_add_ticker_uses_db_when_disconnected(self, config):
        """In disconnected mode, add_ticker writes directly to DB."""
        app = _make_app_with_watchlists(
            config,
            watchlists={"tech": ["AAPL"]},
            socket_path=Path("/nonexistent/path.sock"),
        )
        async with app.run_test():
            assert app.daemon_connected is False
            await app._on_add_result(["NVDA"])
            # Should not crash; NVDA added to watchlist

    @pytest.mark.asyncio
    async def test_remove_ticker_uses_db_when_disconnected(self, config):
        """In disconnected mode, remove_ticker writes directly to DB."""
        app = _make_app_with_watchlists(
            config,
            watchlists={"tech": ["AAPL", "MSFT"]},
            socket_path=Path("/nonexistent/path.sock"),
        )
        async with app.run_test():
            assert app.daemon_connected is False
            app._pending_remove_ticker = "AAPL"
            await app._on_remove_result(True)
            # Should not crash

    @pytest.mark.asyncio
    async def test_delete_watchlist_uses_db_when_disconnected(self, config):
        """In disconnected mode, delete_watchlist writes directly to DB."""
        app = _make_app_with_watchlists(
            config,
            watchlists={"tech": ["AAPL"]},
            socket_path=Path("/nonexistent/path.sock"),
        )
        async with app.run_test():
            assert app.daemon_connected is False
            await app._on_delete_result(True)
            assert "tech" not in app._watchlist_names


# -- Send IPC command ---------------------------------------------------------


class TestSendIPCCommand:
    @pytest.mark.asyncio
    async def test_send_command_with_no_writer(self, config):
        """_send_ipc_command is a no-op when no writer is available."""
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            app._daemon_writer = None
            # Should not raise
            await app._send_ipc_command({"type": "command", "cmd": "refresh"})

    @pytest.mark.asyncio
    async def test_send_command_clears_writer_on_error(self, config):
        """_send_ipc_command clears writer on connection error."""
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            mock_writer = MagicMock()
            mock_writer.write = MagicMock(side_effect=BrokenPipeError)
            mock_writer.drain = AsyncMock()
            app._daemon_writer = mock_writer

            await app._send_ipc_command({"type": "command", "cmd": "refresh"})
            assert app._daemon_writer is None


# -- Socket path configuration -----------------------------------------------


class TestSocketPathConfig:
    def test_default_socket_path(self, config):
        """App uses default socket path from CONFIG_DIR."""
        app = CaracalApp(config=config)
        from caracal.config import CONFIG_DIR

        assert app._socket_path == CONFIG_DIR / "caracal.sock"

    def test_custom_socket_path(self, config, socket_path):
        """App accepts custom socket path."""
        app = CaracalApp(config=config, socket_path=socket_path)
        assert app._socket_path == socket_path


# -- Reconnect timer ----------------------------------------------------------


class TestReconnectTimer:
    @pytest.mark.asyncio
    async def test_disconnect_schedules_reconnect(self, config):
        """Disconnection schedules a 10s reconnect timer."""
        app = _make_app(config, socket_path=Path("/nonexistent/path.sock"))
        async with app.run_test():
            with patch.object(app, "set_timer") as mock_timer:
                app.on_daemon_disconnected(DaemonDisconnected())
                mock_timer.assert_called_once()
                args = mock_timer.call_args[0]
                assert args[0] == 10  # 10 second delay
                assert args[1] == app._start_daemon_connection
