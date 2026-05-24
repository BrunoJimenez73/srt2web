from __future__ import annotations

import logging
from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Select, Static

from cli.client.http_client import LogEntry

logger = logging.getLogger(__name__)

LOG_LEVELS = ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _level_style(level: str) -> str:
    return {
        "INFO": "green",
        "WARNING": "yellow",
        "WARN": "yellow",
        "ERROR": "red",
        "CRITICAL": "red bold",
        "DEBUG": "dim blue",
    }.get(level.upper(), "white")


class TUILogPanel(Static):
    MAX_VISIBLE = 100

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._logs: list[LogEntry] = []
        self._filter: str | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="log-toolbar"):
            yield Static("Logs:", classes="log-title")
            yield Select(
                options=[(lvl, lvl) for lvl in LOG_LEVELS],
                value="ALL",
                id="log-filter-select",
                classes="log-filter",
            )
        yield Static(id="log-content")

    def on_mount(self) -> None:
        self._refresh()

    def update_logs(self, logs: list[LogEntry]) -> None:
        self._logs = logs
        self._refresh()

    @on(Select.Changed, "#log-filter-select")
    def _on_filter_changed(self, event: Select.Changed) -> None:
        val = event.value
        self._filter = None if val == "ALL" else str(val)
        self._refresh()

    def set_filter(self, level: str | None) -> None:
        self._filter = level
        self._refresh()
        try:
            sel = self.query_one("#log-filter-select", Select)
            sel.value = level or "ALL"
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)

    def _refresh(self) -> None:
        visible = self._logs[-self.MAX_VISIBLE :]
        if self._filter:
            visible = [e for e in visible if e.level.upper() == self._filter.upper()]
            visible = visible[-self.MAX_VISIBLE :]

        content = self.query_one("#log-content", Static)
        if not visible:
            content.update(Text("No logs", style="dim"))
            return

        t = Text()
        for entry in visible:
            time_str = entry.time_str or ""
            t.append(time_str, style="dim")
            t.append(" | ")
            t.append(entry.level.ljust(8), style=_level_style(entry.level))
            t.append(" | ")
            t.append(entry.message)
            t.append("\n")
        content.update(t)
