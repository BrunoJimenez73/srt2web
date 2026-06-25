"""
Webhook Manager - Dispara notificaciones HTTP ante eventos del pipeline.

Características:
✅ Cola de eventos asíncrona (no bloquea el pipeline)
✅ Retry con backoff (1s, 5s, 15s - 3 intentos)
✅ Timeout por request: 5s
✅ Fácilmente extensible con nuevos tipos de evento
"""

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("srt2web.webhook_manager")


@dataclass
class WebhookEvent:
    """Evento a ser enviado a un webhook."""

    event_type: str
    data: dict[str, Any]
    timestamp: float = field(default_factory=time.time)

    def to_payload(self) -> str:
        return json.dumps(
            {
                "event": self.event_type,
                "timestamp": self.timestamp,
                "data": self.data,
            }
        )


@dataclass
class WebhookTarget:
    """Un destino de webhook configurado."""

    url: str
    events: list[str]
    secret: str = ""
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 5.0

    @property
    def backoff_delays(self) -> list[float]:
        return [1.0, 5.0, 15.0]


class WebhookManager:
    """
    Manager de webhooks: cola, dispatch, retry.

    Uso:
        manager = WebhookManager()
        manager.add_target(WebhookTarget(url="https://hooks.slack.com/...", events=["start", "error"]))
        manager.emit("pipeline.start", {"state": "running"})
    """

    def __init__(self) -> None:
        self._targets: list[WebhookTarget] = []
        self._queue: asyncio.Queue[WebhookEvent] = asyncio.Queue()
        self._worker_task: asyncio.Task[None] | None = None
        self._running = False

    def add_target(self, target: WebhookTarget) -> None:
        self._targets.append(target)
        logger.info(f"Webhook target added: {target.url} (events: {target.events})")

    def clear_targets(self) -> None:
        self._targets.clear()

    def set_targets(self, targets: list[WebhookTarget]) -> None:
        self._targets = targets

    def emit(self, event_type: str, data: dict[str, Any]) -> None:
        """Enqueue an event for dispatch (thread-safe via put_nowait)."""
        event = WebhookEvent(event_type=event_type, data=data)
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning(f"Webhook queue full, dropping event: {event_type}")

    async def start(self) -> None:
        """Start the background worker."""
        if self._running:
            return
        self._running = True
        self._worker_task = asyncio.create_task(self._worker_loop())
        logger.info("Webhook manager started")

    async def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None
        logger.info("Webhook manager stopped")

    async def _worker_loop(self) -> None:
        """Background loop: process events from the queue."""

        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except TimeoutError:
                continue

            payload = event.to_payload()
            relevant = [t for t in self._targets if event.event_type in t.events]

            for target in relevant:
                await self._dispatch(target, payload, event.event_type)

    async def _dispatch(self, target: WebhookTarget, payload: str, event_type: str) -> None:
        """Dispatch to a single target with retry logic."""
        import httpx

        headers = {"Content-Type": "application/json"}
        if target.secret:
            headers["X-Webhook-Secret"] = target.secret

        for attempt in range(target.max_retries):
            try:
                async with httpx.AsyncClient(timeout=target.timeout) as client:
                    response = await client.post(target.url, content=payload, headers=headers)
                    if response.is_success:
                        logger.debug(f"Webhook sent: {event_type} -> {target.url} (attempt {attempt + 1})")
                        return
                    logger.warning(f"Webhook {target.url} returned {response.status_code} for {event_type}")
            except httpx.TimeoutException:
                logger.warning(f"Webhook {target.url} timed out for {event_type} (attempt {attempt + 1})")
            except httpx.RequestError as e:
                logger.warning(f"Webhook {target.url} connection error: {e} (attempt {attempt + 1})")
            except Exception as e:
                logger.error(f"Webhook {target.url} unexpected error: {e}")

            if attempt < target.max_retries - 1:
                delay = target.backoff_delays[attempt] if attempt < len(target.backoff_delays) else 15.0
                await asyncio.sleep(delay)

        logger.error(f"Webhook {target.url} failed after {target.max_retries} attempts for {event_type}")


# Singleton global
webhook_manager = WebhookManager()
