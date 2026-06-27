from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Static


class RecordingsScreen(Screen[Any]):
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

    .rec-item {
        height: auto;
        padding: 0 2;
    }

    .rec-name {
        color: $text;
        text-style: bold;
    }

    .rec-meta {
        color: $text-muted;
    }

    .action-bar {
        height: 3;
        margin: 1 2;
    }

    .summary-bar {
        height: 3;
        padding: 0 2;
        color: $text-muted;
        margin-bottom: 1;
    }
    """

    BINDINGS = [  # noqa: RUF012
        ("escape", "app.pop_screen", "Back"),
        ("d", "delete_recording", "Delete"),
        ("r", "refresh", "Refresh"),
    ]

    def __init__(self, api_client: Any):
        super().__init__()
        self.api_client = api_client
        self._recordings: list[dict[str, Any]] = []
        self._selected: int = 0

    def compose(self) -> ComposeResult:
        yield Static("Recordings", classes="screen-title")
        yield Static("", id="summary-bar", classes="summary-bar")
        with ScrollableContainer(id="rec-list"):
            yield Static("Loading...", id="rec-content")
        with Horizontal(classes="action-bar"):
            yield Button("Refresh", id="btn-refresh")
            yield Button("Back", id="btn-back", variant="default")

    async def on_mount(self) -> None:
        await self._load_recordings()

    async def _load_recordings(self) -> None:
        try:
            data = await self.api_client.get_recordings()
            if isinstance(data, list):
                self._recordings = data
            elif isinstance(data, dict):
                self._recordings = data.get("recordings", [])
            else:
                self._recordings = []
        except Exception as e:
            self.app.notify(f"Error loading recordings: {e}", severity="error", timeout=5)
            self._recordings = []
        self._render()

    def _display(self) -> None:
        try:
            content = self.query_one("#rec-content", Static)
            summary = self.query_one("#summary-bar", Static)
        except Exception:
            # UI elements not yet mounted, skip render — expected during startup
            return

        summary.update(Text(f"{len(self._recordings)} recording(s)", style="dim"))

        if not self._recordings:
            content.update(Text("No recordings available.", style="dim"))
            return

        t = Text()
        for i, rec in enumerate(self._recordings):
            name = rec.get("name", "?")
            size = rec.get("size_formatted", rec.get("size_bytes", ""))
            modified = rec.get("modified", "")
            fmt = rec.get("format", "")
            marker = "▸" if i == self._selected else " "

            t.append(f"\n{marker} {name}\n", style="bold" if i == self._selected else "")
            parts = []
            if size:
                parts.append(str(size))
            if fmt:
                parts.append(fmt)
            if modified:
                parts.append(modified)
            if parts:
                t.append(f"   {' | '.join(parts)}\n", style="dim")

        t.append("\n\n[dim]Keys: [D]elete  [R]efresh  [Esc] Back[/]")
        content.update(t)

    @on(Button.Pressed, "#btn-refresh")
    async def on_refresh(self) -> None:
        await self._load_recordings()

    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:
        self.app.pop_screen()

    async def action_delete_recording(self) -> None:
        if not self._recordings:
            self.app.notify("No recordings to delete", severity="warning", timeout=3)
            return
        rec = self._recordings[self._selected]
        name = rec.get("name", "")
        try:
            await self.api_client.delete_recording(name)
            self.app.notify(f"Deleted '{name}'", severity="information", timeout=3)
            if self._selected >= len(self._recordings) - 1:
                self._selected = max(0, len(self._recordings) - 2)
            await self._load_recordings()
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=5)

    async def action_refresh(self) -> None:
        await self._load_recordings()
