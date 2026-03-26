"""Tests for the IPC server (Unix socket with JSON-Lines protocol)."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
import pytest_asyncio

from caracal.config import CaracalConfig
from caracal.daemon.ipc import IPCServer
from caracal.daemon.registry import (
    IntervalTrigger,
    TaskContext,
    TaskRegistry,
    TaskResult,
)
from caracal.daemon.scheduler import scheduler_loop
from caracal.storage.duckdb import DuckDBStorage

# -- Helpers ---


async def connect_client(
    socket_path: Path,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Connect to the IPC server and return reader/writer pair."""
    reader, writer = await asyncio.open_unix_connection(str(socket_path))
    return reader, writer


async def send_message(writer: asyncio.StreamWriter, message: dict) -> None:
    """Send a JSON-Lines message to the server."""
    data = json.dumps(message).encode("utf-8") + b"\n"
    writer.write(data)
    await writer.drain()


async def recv_message(reader: asyncio.StreamReader, timeout: float = 2.0) -> dict:
    """Read a single JSON-Lines message from the server."""
    line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    return json.loads(line.decode("utf-8").strip())


def close_writer(writer: asyncio.StreamWriter) -> None:
    """Close a writer, ignoring errors."""
    try:
        writer.close()
    except Exception:
        pass


# -- Fixtures ---


@pytest.fixture
def socket_path(tmp_path):
    """Temporary socket path for tests."""
    return tmp_path / "test.sock"


@pytest.fixture
def storage():
    """In-memory DuckDB storage for IPC tests."""
    s = DuckDBStorage(":memory:")
    yield s
    s.close()


@pytest.fixture
def context(storage):
    """Task context for IPC tests."""
    return TaskContext(db=storage, config=CaracalConfig())


@pytest_asyncio.fixture
async def ipc_server(socket_path, context):
    """Running IPC server for tests. Shuts down automatically."""
    server = IPCServer(socket_path=socket_path, context=context)
    await server.start()
    yield server
    await server.shutdown()


# -- IPCServer lifecycle tests ---


class TestIPCServerLifecycle:
    @pytest.mark.asyncio
    async def test_start_creates_socket_file(self, socket_path, context):
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()
        assert socket_path.exists()
        await server.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown_removes_socket_file(self, socket_path, context):
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()
        await server.shutdown()
        assert not socket_path.exists()

    @pytest.mark.asyncio
    async def test_start_removes_stale_socket(self, socket_path, context):
        # Create a stale socket file
        socket_path.touch()
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()
        assert socket_path.exists()
        await server.shutdown()

    @pytest.mark.asyncio
    async def test_start_creates_parent_dirs(self, tmp_path, context):
        socket_path = tmp_path / "nested" / "dir" / "test.sock"
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()
        assert socket_path.exists()
        await server.shutdown()

    @pytest.mark.asyncio
    async def test_initial_client_count_is_zero(self, ipc_server):
        assert ipc_server.client_count == 0


# -- Subscribe tests ---


class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_adds_client(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "subscribe"})
        response = await recv_message(reader)

        assert response["type"] == "result"
        assert response["cmd"] == "subscribe"
        assert response["status"] == "ok"
        assert ipc_server.client_count == 1

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_subscribe_multiple_clients(self, ipc_server, socket_path):
        clients = []
        for _ in range(3):
            reader, writer = await connect_client(socket_path)
            await send_message(writer, {"type": "subscribe"})
            response = await recv_message(reader)
            assert response["status"] == "ok"
            clients.append((reader, writer))

        assert ipc_server.client_count == 3

        for _, writer in clients:
            close_writer(writer)


# -- Broadcast tests ---


class TestBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_to_single_client(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "subscribe"})
        await recv_message(reader)  # consume subscribe response

        msg = {"type": "task_complete", "task": "FetchTask", "items": 5}
        await ipc_server.broadcast(msg)

        received = await recv_message(reader)
        assert received == msg

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_clients(self, ipc_server, socket_path):
        clients = []
        for _ in range(3):
            reader, writer = await connect_client(socket_path)
            await send_message(writer, {"type": "subscribe"})
            await recv_message(reader)  # consume subscribe response
            clients.append((reader, writer))

        msg = {"type": "data_update", "table": "quotes"}
        await ipc_server.broadcast(msg)

        for reader, _ in clients:
            received = await recv_message(reader)
            assert received == msg

        for _, writer in clients:
            close_writer(writer)

    @pytest.mark.asyncio
    async def test_broadcast_no_clients_no_error(self, ipc_server):
        # Should not raise when no clients are connected
        await ipc_server.broadcast({"type": "test"})

    @pytest.mark.asyncio
    async def test_broadcast_only_to_subscribed(self, ipc_server, socket_path):
        # Client connects but does NOT subscribe
        reader_unsub, writer_unsub = await connect_client(socket_path)

        # Client subscribes
        reader_sub, writer_sub = await connect_client(socket_path)
        await send_message(writer_sub, {"type": "subscribe"})
        await recv_message(reader_sub)

        msg = {"type": "task_complete", "task": "Test", "items": 1}
        await ipc_server.broadcast(msg)

        # Subscribed client receives it
        received = await recv_message(reader_sub)
        assert received == msg

        # Unsubscribed client should NOT receive it (timeout)
        with pytest.raises(asyncio.TimeoutError):
            await recv_message(reader_unsub, timeout=0.2)

        close_writer(writer_unsub)
        close_writer(writer_sub)


# -- Client disconnect tests ---


class TestClientDisconnect:
    @pytest.mark.asyncio
    async def test_disconnect_removes_client(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "subscribe"})
        await recv_message(reader)
        assert ipc_server.client_count == 1

        writer.close()
        await writer.wait_closed()

        # Give the server time to detect the disconnect
        await asyncio.sleep(0.1)

        # Broadcast to trigger cleanup of dead client
        await ipc_server.broadcast({"type": "test"})
        # After broadcast, dead client should be removed
        assert ipc_server.client_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_does_not_affect_other_clients(
        self, ipc_server, socket_path
    ):
        # Connect two clients
        reader1, writer1 = await connect_client(socket_path)
        await send_message(writer1, {"type": "subscribe"})
        await recv_message(reader1)

        reader2, writer2 = await connect_client(socket_path)
        await send_message(writer2, {"type": "subscribe"})
        await recv_message(reader2)

        assert ipc_server.client_count == 2

        # Disconnect client 1
        writer1.close()
        await writer1.wait_closed()
        await asyncio.sleep(0.1)

        # Broadcast should still work for client 2
        msg = {"type": "data_update", "table": "news"}
        await ipc_server.broadcast(msg)

        received = await recv_message(reader2)
        assert received == msg

        close_writer(writer2)


# -- Command dispatch tests ---


class TestCommandRefresh:
    @pytest.mark.asyncio
    async def test_refresh_command(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response = await recv_message(reader)

        assert response["type"] == "result"
        assert response["cmd"] == "refresh"
        assert response["status"] == "ok"

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_refresh_calls_callback(self, socket_path, context):
        callback_called = asyncio.Event()

        async def mock_callback():
            callback_called.set()

        server = IPCServer(
            socket_path=socket_path,
            context=context,
            run_tasks_callback=mock_callback,
        )
        await server.start()

        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response = await recv_message(reader)
        assert response["status"] == "ok"

        # Wait for the background task to execute
        await asyncio.wait_for(callback_called.wait(), timeout=2.0)
        assert callback_called.is_set()

        close_writer(writer)
        await server.shutdown()


class TestCommandCreateWatchlist:
    @pytest.mark.asyncio
    async def test_create_watchlist(self, ipc_server, socket_path, storage):
        reader, writer = await connect_client(socket_path)
        await send_message(
            writer,
            {"type": "command", "cmd": "create_watchlist", "name": "tech"},
        )
        response = await recv_message(reader)

        assert response["type"] == "result"
        assert response["cmd"] == "create_watchlist"
        assert response["status"] == "ok"
        assert response["name"] == "tech"

        # Verify watchlist was created in DB
        assert storage.watchlist_exists("tech")

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_create_watchlist_missing_name(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "command", "cmd": "create_watchlist"})
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert response["cmd"] == "create_watchlist"
        assert "name" in response["msg"].lower()

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_create_duplicate_watchlist_returns_error(
        self, ipc_server, socket_path, storage
    ):
        storage.create_watchlist("existing")

        reader, writer = await connect_client(socket_path)
        await send_message(
            writer,
            {
                "type": "command",
                "cmd": "create_watchlist",
                "name": "existing",
            },
        )
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert response["msg"] == "Failed to create watchlist"

        close_writer(writer)


class TestCommandAddTicker:
    @pytest.mark.asyncio
    async def test_add_ticker(self, ipc_server, socket_path, storage):
        storage.create_watchlist("tech")

        reader, writer = await connect_client(socket_path)
        await send_message(
            writer,
            {
                "type": "command",
                "cmd": "add_ticker",
                "watchlist": "tech",
                "tickers": ["NVDA", "AMD"],
            },
        )
        response = await recv_message(reader)

        assert response["type"] == "result"
        assert response["cmd"] == "add_ticker"
        assert response["status"] == "ok"

        # Verify tickers were added
        items = storage.get_watchlist_items("tech")
        assert "NVDA" in items
        assert "AMD" in items

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_add_ticker_missing_watchlist(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(
            writer,
            {"type": "command", "cmd": "add_ticker", "tickers": ["AAPL"]},
        )
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert "watchlist" in response["msg"].lower()

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_add_ticker_missing_tickers(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(
            writer,
            {"type": "command", "cmd": "add_ticker", "watchlist": "tech"},
        )
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert "tickers" in response["msg"].lower()

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_add_ticker_nonexistent_watchlist(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(
            writer,
            {
                "type": "command",
                "cmd": "add_ticker",
                "watchlist": "nonexistent",
                "tickers": ["AAPL"],
            },
        )
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert response["msg"] == "Failed to add ticker"

        close_writer(writer)


class TestQueryStatus:
    @pytest.mark.asyncio
    async def test_status_query(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "query", "cmd": "status"})
        response = await recv_message(reader)

        assert response["type"] == "status"
        assert "clients" in response
        assert "recent_runs" in response

        close_writer(writer)


# -- Error handling tests ---


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_unknown_message_type(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "bogus"})
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert "unknown" in response["msg"].lower()

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_unknown_command(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "command", "cmd": "nonexistent"})
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert "unknown" in response["msg"].lower()

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_invalid_json(self, ipc_server, socket_path):
        reader, writer = await connect_client(socket_path)
        writer.write(b"not valid json\n")
        await writer.drain()
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert "invalid json" in response["msg"].lower()

        close_writer(writer)


# -- Shutdown tests ---


class TestShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_sends_notification(self, socket_path, context):
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()

        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "subscribe"})
        await recv_message(reader)  # subscribe response

        await server.shutdown()

        # Client should receive shutdown notification
        msg = await recv_message(reader, timeout=2.0)
        assert msg["type"] == "shutdown"

        close_writer(writer)

    @pytest.mark.asyncio
    async def test_shutdown_removes_socket(self, socket_path, context):
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()
        assert socket_path.exists()
        await server.shutdown()
        assert not socket_path.exists()

    @pytest.mark.asyncio
    async def test_shutdown_clears_clients(self, socket_path, context):
        server = IPCServer(socket_path=socket_path, context=context)
        await server.start()

        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "subscribe"})
        await recv_message(reader)
        assert server.client_count == 1

        await server.shutdown()
        assert server.client_count == 0

        close_writer(writer)


# -- Scheduler on_event callback tests ---


class TestSchedulerEventCallback:
    @pytest.mark.asyncio
    async def test_on_event_called_on_success(self):
        events: list[dict] = []

        async def capture_event(event: dict) -> None:
            events.append(event)

        @dataclass
        class SuccessTask:
            name: str = "test_task"

            async def run(self, ctx: TaskContext) -> TaskResult:
                return TaskResult(status="ok", items_processed=42)

        storage = DuckDBStorage(":memory:")
        ctx = TaskContext(db=storage, config=CaracalConfig())
        registry = TaskRegistry()
        registry.register(SuccessTask(), IntervalTrigger(minutes=0))

        async def run_briefly():
            await asyncio.wait_for(
                scheduler_loop(registry, ctx, on_event=capture_event),
                timeout=0.3,
            )

        with pytest.raises(asyncio.TimeoutError):
            await run_briefly()

        storage.close()

        # Should have at least one task_complete event
        complete_events = [e for e in events if e["type"] == "task_complete"]
        assert len(complete_events) >= 1
        assert complete_events[0]["task"] == "test_task"
        assert complete_events[0]["items"] == 42

    @pytest.mark.asyncio
    async def test_on_event_called_on_error(self):
        events: list[dict] = []

        async def capture_event(event: dict) -> None:
            events.append(event)

        @dataclass
        class FailTask:
            name: str = "fail_task"

            async def run(self, ctx: TaskContext) -> TaskResult:
                return TaskResult(status="error", message="something broke")

        storage = DuckDBStorage(":memory:")
        ctx = TaskContext(db=storage, config=CaracalConfig())
        registry = TaskRegistry()
        registry.register(FailTask(), IntervalTrigger(minutes=60))

        async def run_briefly():
            await asyncio.wait_for(
                scheduler_loop(
                    registry,
                    ctx,
                    retry_delay_seconds=0,
                    on_event=capture_event,
                ),
                timeout=0.5,
            )

        with pytest.raises(asyncio.TimeoutError):
            await run_briefly()

        storage.close()

        # Should have error events (initial failure + retry failure)
        error_events = [e for e in events if e["type"] == "error"]
        assert len(error_events) >= 1
        assert error_events[0]["task"] == "fail_task"
        assert error_events[0]["msg"] == "Task fail_task failed"

    @pytest.mark.asyncio
    async def test_on_event_none_is_safe(self):
        """Scheduler works normally when on_event is None (backward compat)."""

        @dataclass
        class QuickTask:
            name: str = "quick"
            count: int = 0

            async def run(self, ctx: TaskContext) -> TaskResult:
                self.count += 1
                if self.count >= 2:
                    raise asyncio.CancelledError
                return TaskResult(status="ok", items_processed=1)

        storage = DuckDBStorage(":memory:")
        ctx = TaskContext(db=storage, config=CaracalConfig())
        registry = TaskRegistry()
        task = QuickTask()
        registry.register(task, IntervalTrigger(minutes=0))

        with pytest.raises(asyncio.CancelledError):
            await scheduler_loop(registry, ctx, on_event=None)

        storage.close()
        assert task.count == 2


# -- Error sanitization tests ---


class TestErrorSanitization:
    @pytest.mark.asyncio
    async def test_status_error_returns_generic_message(self, socket_path):
        """Status query on broken DB returns generic error."""
        s = DuckDBStorage(":memory:")
        ctx = TaskContext(db=s, config=CaracalConfig())
        s.close()  # close DB to force errors

        server = IPCServer(socket_path=socket_path, context=ctx)
        await server.start()

        reader, writer = await connect_client(socket_path)
        await send_message(writer, {"type": "query", "cmd": "status"})
        response = await recv_message(reader)

        assert response["type"] == "error"
        assert response["msg"] == "Failed to get status"

        close_writer(writer)
        await server.shutdown()


# -- Refresh rate limiting tests ---


class TestRefreshRateLimit:
    @pytest.mark.asyncio
    async def test_refresh_rejected_within_cooldown(self, socket_path, context):
        """Second refresh within cooldown period should be rejected."""
        callback_called = asyncio.Event()

        async def mock_callback():
            callback_called.set()

        server = IPCServer(
            socket_path=socket_path,
            context=context,
            run_tasks_callback=mock_callback,
            refresh_cooldown_seconds=60,
        )
        await server.start()

        reader, writer = await connect_client(socket_path)

        # First refresh should succeed
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response1 = await recv_message(reader)
        assert response1["status"] == "ok"

        # Wait for the background task to complete
        await asyncio.wait_for(callback_called.wait(), timeout=2.0)
        await asyncio.sleep(0.05)

        # Second refresh should be rejected (within cooldown)
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response2 = await recv_message(reader)
        assert response2["type"] == "error"
        assert "cooldown" in response2["msg"].lower()

        close_writer(writer)
        await server.shutdown()

    @pytest.mark.asyncio
    async def test_refresh_allowed_after_cooldown(self, socket_path, context):
        """Both refreshes should succeed when cooldown is 0."""
        call_count = 0

        async def mock_callback():
            nonlocal call_count
            call_count += 1

        server = IPCServer(
            socket_path=socket_path,
            context=context,
            run_tasks_callback=mock_callback,
            refresh_cooldown_seconds=0,
        )
        await server.start()

        reader, writer = await connect_client(socket_path)

        # First refresh
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response1 = await recv_message(reader)
        assert response1["status"] == "ok"

        # Wait for the first task to complete
        await asyncio.sleep(0.1)

        # Second refresh should also succeed (cooldown=0)
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response2 = await recv_message(reader)
        assert response2["status"] == "ok"

        close_writer(writer)
        await server.shutdown()

    @pytest.mark.asyncio
    async def test_concurrent_refresh_prevented(self, socket_path, context):
        """Refresh while another is still running should be rejected."""
        blocker = asyncio.Event()

        async def slow_callback():
            await blocker.wait()

        server = IPCServer(
            socket_path=socket_path,
            context=context,
            run_tasks_callback=slow_callback,
            refresh_cooldown_seconds=0,
        )
        await server.start()

        reader, writer = await connect_client(socket_path)

        # First refresh starts but blocks on the event
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response1 = await recv_message(reader)
        assert response1["status"] == "ok"

        # Give the task a moment to start running
        await asyncio.sleep(0.05)

        # Second refresh should be rejected (first is still running)
        await send_message(writer, {"type": "command", "cmd": "refresh"})
        response2 = await recv_message(reader)
        assert response2["type"] == "error"
        assert "already running" in response2["msg"].lower()

        # Unblock the first refresh so cleanup is clean
        blocker.set()
        await asyncio.sleep(0.05)

        close_writer(writer)
        await server.shutdown()
