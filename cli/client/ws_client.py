from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Callable

import websockets

from cli.client.http_client import LogEntry


class WSClient:
    def __init__(
        self,
        url: str,
        token: str | None = None,
        on_log: Callable[[LogEntry], None] | None = None,
        on_status: Callable[[dict], None] | None = None,
        on_health: Callable[[dict], None] | None = None,
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
        self._reconnect_count = 0
        self._max_reconnect = 5
        self._backoff_base = 1.0
        self._max_backoff = 30.0
        self._jitter = 0.5
        self._manual_disconnect = False
        self._task: asyncio.Task | None = None

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
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self.on_connection_change:
            self.on_connection_change(False)

    def _get_backoff_delay(self) -> float:
        delay = min(self._backoff_base * (2 ** self._reconnect_count), self._max_backoff)
        jitter = random.uniform(0, self._jitter)
        return delay + jitter

    async def _run(self) -> None:
        if self.on_connection_change:
            self.on_connection_change(False)

        while self._running and self._reconnect_count < self._max_reconnect:
            try:
                extra_headers = {}
                if self.token:
                    extra_headers["Authorization"] = f"Bearer {self.token}"

                async with websockets.connect(
                    self.url,
                    additional_headers=extra_headers,
                    ping_interval=30,
                    ping_timeout=10,
                    close_timeout=5,
                ) as ws:
                    self._ws = ws
                    self._reconnect_count = 0
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

            if self._running and not self._manual_disconnect:
                if self.on_connection_change:
                    self.on_connection_change(False)
                delay = self._get_backoff_delay()
                self._reconnect_count += 1
                await asyncio.sleep(delay)

        if self.on_connection_change:
            self.on_connection_change(False)

    def _handle_message(self, msg: dict) -> None:
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
