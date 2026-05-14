from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static


class TUIModuleCard(Static):
    def __init__(self, module_name: str, id: str | None = None):
        super().__init__(id=id)
        self.module_name = module_name
        self._state = "idle"
        self._enabled = True
        self._chunks = 0
        self._last_time = 0.0
        self._extra: dict = {}

    def on_mount(self) -> None:
        self._refresh()

    def update(self, state: str, enabled: bool, chunks: int, last_time: float, extra: dict | None = None) -> None:
        self._state = state
        self._enabled = enabled
        self._chunks = chunks
        self._last_time = last_time
        self._extra = extra or {}
        self._refresh()

    def _refresh(self) -> None:
        state_style = {
            "running": "green",
            "processing": "green",
            "starting": "yellow",
            "initializing": "blue",
            "stopping": "yellow",
            "stopped": "dim white",
            "idle": "dim white",
            "error": "red",
            "degraded": "orange1",
            "disabled": "dim",
        }.get(self._state, "white")

        if not self._enabled:
            state_dot = Text("—", style="dim")
        elif self._state in ("running", "processing"):
            state_dot = Text("●", style=f"bold {state_style}")
        elif self._state in ("error",):
            state_dot = Text("✖", style=f"bold {state_style}")
        elif self._state in ("degraded",):
            state_dot = Text("⚠", style=f"bold {state_style}")
        else:
            state_dot = Text("●", style=state_style)

        label = self.module_name.replace("_", " ").title()
        extra_str = ""
        if self._extra.get("using_gpu"):
            extra_str += "GPU "
        elif self._extra.get("device"):
            extra_str += self._extra["device"] + " "

        t = Text.assemble(
            state_dot,
            (" ",),
            (f"{label}", "bold"),
            "\n",
            (f"  {self._state}", state_style),
            (" | " if self._chunks else "", "dim"),
            (f"{self._chunks}ch" if self._chunks else "", "dim"),
            (" | " if self._last_time else "", "dim"),
            (f"{self._last_time:.0f}ms" if self._last_time else "", "dim"),
            "\n",
            (f"  {extra_str}" if extra_str else "", "dim"),
        )
        super().update(t)
