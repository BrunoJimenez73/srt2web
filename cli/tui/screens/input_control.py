from __future__ import annotations

import logging
from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Input, Static

from cli.client.http_client import APIClient

logger = logging.getLogger(__name__)


class InputControlScreen(Screen[Any]):
    CSS = """
    Screen {
        background: $surface;
    }

    .screen-title {
        color: $text;
        text-style: bold;
        padding: 1 2;
        margin-bottom: 1;
    }

    .info-row {
        height: 3;
        padding: 0 2;
        color: $text;
    }

    .control-bar {
        height: 3;
        margin: 1 2;
        align: center middle;
    }

    .seek-area {
        height: 5;
        margin: 1 2;
        padding: 1;
        border: solid $border;
    }

    .input-type-label {
        color: $accent;
        text-style: bold;
        padding: 0 2;
        margin-top: 1;
    }
    """

    BINDINGS = [  # noqa: RUF012
        ("escape", "app.pop_screen", "Back"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self._input_info: dict[str, Any] = {}
        self._status: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Static("Input Control", classes="screen-title")
        yield Static("Input Type: --", id="input-type", classes="input-type-label")
        with ScrollableContainer(id="input-details"):
            yield Static("Loading input info...", id="input-content")
        with Horizontal(classes="control-bar"):
            yield Button("Play", id="btn-play", variant="primary")
            yield Button("Pause", id="btn-pause")
            yield Button("Stop", id="btn-stop", variant="error")
        with Horizontal(classes="seek-area"):
            yield Static("Seek:", classes="info-row")
            yield Input(placeholder="Position (seconds)...", id="seek-input")
            yield Button("Go", id="btn-seek", variant="default")
        yield Static("", id="status-msg", classes="info-row")

    async def on_mount(self) -> None:
        await self._refresh()

    async def _refresh(self) -> None:
        try:
            info = await self.api_client.get_input_info()
            self._input_info = info if isinstance(info, dict) else {}
            status = await self.api_client.get_status()
            self._status = {"state": status.state} if hasattr(status, "state") else {}
        except Exception as e:
            self._input_info = {}
            self._status = {}
            self.app.notify(f"Error: {e}", severity="error", timeout=3)
        self._display()

    def _display(self) -> None:
        type_label = self.query_one("#input-type", Static)
        content = self.query_one("#input-content", Static)

        input_type = self._input_info.get("type", "unknown")
        type_label.update(f"Input Type: {input_type.upper()}")

        if not self._input_info:
            content.update(Text("No input connected.", style="dim"))
            return

        t = Text()
        for k, v in self._input_info.items():
            t.append(f"  {k}: {v}\n", style="dim" if k == "type" else "")
        content.update(t)

    @on(Button.Pressed, "#btn-play")
    async def on_play(self) -> None:
        try:
            result = await self.api_client.control_input("play")
            self._show_status("Playing" if result.get("status") == "playing" else str(result))
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=3)

    @on(Button.Pressed, "#btn-pause")
    async def on_pause(self) -> None:
        try:
            result = await self.api_client.control_input("pause")
            self._show_status("Paused" if result.get("status") == "paused" else str(result))
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=3)

    @on(Button.Pressed, "#btn-stop")
    async def on_stop(self) -> None:
        try:
            await self.api_client.stop_pipeline()
            self._show_status("Pipeline stopped")
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=3)

    @on(Button.Pressed, "#btn-seek")
    async def on_seek(self) -> None:
        inp = self.query_one("#seek-input", Input)
        try:
            pos = float(inp.value)
        except (ValueError, TypeError):
            self.app.notify("Enter a valid number", severity="warning", timeout=3)
            return
        try:
            result = await self.api_client.control_input("seek", {"position": pos})
            self._show_status(f"Seeked to {pos}s" if result.get("status") == "seeked" else str(result))
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=3)

    def _show_status(self, msg: str) -> None:
        try:
            self.query_one("#status-msg", Static).update(f"Status: {msg}")
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)

    async def action_refresh(self) -> None:
        await self._refresh()
