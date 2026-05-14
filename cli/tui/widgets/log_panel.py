from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from cli.client.http_client import LogEntry


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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._logs: list[LogEntry] = []
        self._filter: str | None = None

    def on_mount(self) -> None:
        self._refresh()

    def update_logs(self, logs: list[LogEntry]) -> None:
        self._logs = logs
        self._refresh()

    def set_filter(self, level: str | None) -> None:
        self._filter = level
        self._refresh()

    def _refresh(self) -> None:
        visible = self._logs[-self.MAX_VISIBLE:]
        if self._filter:
            visible = [e for e in visible if e.level.upper() == self._filter.upper()]
            visible = visible[-self.MAX_VISIBLE:]

        if not visible:
            self.update(Text("No logs", style="dim"))
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
        self.update(t)
