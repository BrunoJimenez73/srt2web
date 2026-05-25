from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import random
from collections.abc import Callable
from typing import Any

import websockets

from cli.client.http_client import LogEntry


class WSClient:
    def __init__(
        self,
        url: str,
        token: str | None = None,
        on_log: Callable[[LogEntry], None] | None = None,
        on_status: Callable[[dict[str, Any]], None] | None = None,
        on_health: Callable[[dict[str, Any]], None] | None = None,
        on_connection_change: Callable[[bool], None] | None = None,
    ):
        self.url = url.rstrip("/").replace("http://", "ws://").replace("https://", "wss://")
        self.url += "/ws/logs"
        self.token = token
        self.on_log = on_log
        self.on_status = on_status
        self.on_health = on_health
        self.on_connection_change = on_connection_change
        self._ws: Any = None
        self._running = False
        self._reconnect_count: int = 0
        self._max_reconnect: int = 5
        self._backoff_base: float = 1.0
        self._max_backoff: float = 30.0
        self._jitter: float = 0.5
        self._manual_disconnect = False
        self._task: asyncio.Task[Any] | None = None

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def connect(self) -> None:
        self._manual_disconnect = False
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def disconnect(self) -> None:
        self._manual_disconnect = True
        self._running = False
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await self._task
            self._task = None
        if self.on_connection_change:
            self.on_connection_change(False)

    def _get_backoff_delay(self) -> float:
        delay: float = min(self._backoff_base * (2**self._reconnect_count), self._max_backoff)
        jitter: float = random.uniform(0, self._jitter)
        return delay + jitter

    async def _run(self) -> None:
        if self.on_connection_change:
            self.on_connection_change(False)

        while self._running and self._reconnect_count < self._max_reconnect:
            try:
                async with websockets.connect(
                    self.url,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._reconnect_count = 0

                    # Auth handshake: send token as message if configured
                    if self.token:
                        await ws.send(json.dumps({"type": "auth", "token": self.token}))
                        auth_response = await asyncio.wait_for(ws.recv(), timeout=10)
                        auth_msg = json.loads(auth_response)
                        if auth_msg.get("type") != "auth_ok":
                            logger = logging.getLogger("srt2web.cli.ws")
                            logger.warning("WebSocket auth failed: %s", auth_msg)
                            await ws.close()
                            break

                    if self.on_connection_change:
                        self.on_connection_change(True)

                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        self._handle_message(msg)

            except (asyncio.CancelledError, websockets.exceptions.ConnectionClosed):
                if self._manual_disconnect:
                    break
            except Exception:
                if self._manual_disconnect:
                    break
                # Connection error, will attempt reconnect with backoff

            if self._running and not self._manual_disconnect:
                if self.on_connection_change:
                    self.on_connection_change(False)
                delay = self._get_backoff_delay()
                self._reconnect_count += 1
                await asyncio.sleep(delay)

        if self.on_connection_change:
            self.on_connection_change(False)

    def _handle_message(self, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type", "")
        if msg_type == "log":
            entry = LogEntry.from_dict(msg)
            if self.on_log:
                self.on_log(entry)
        elif msg_type == "status":
            if self.on_status:
                self.on_status(msg.get("status", msg))
        elif msg_type == "output_health":
            if self.on_health:
                self.on_health(msg)
