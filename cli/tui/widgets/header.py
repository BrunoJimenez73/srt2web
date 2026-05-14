from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static


class TUIHeader(Static):
    ws_connected = reactive(False)
    pipeline_state = reactive("stopped")

    def on_mount(self) -> None:
        self.set_interval(1, self._refresh_clock)
        self._refresh_clock()

    def watch_pipeline_state(self, value: str) -> None:
        self._refresh_clock()

    def watch_ws_connected(self, value: bool) -> None:
        self._refresh_clock()

    def _refresh_clock(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        state_style = {
            "running": "bold green",
            "starting": "bold yellow",
            "stopping": "bold yellow",
            "stopped": "white",
            "error": "bold red",
            "idle": "dim white",
        }.get(self.pipeline_state, "white")

        ws_icon = "●" if self.ws_connected else "○"
        ws_style = "green" if self.ws_connected else "red"

        self.update(
            Text.assemble(
                (f" {ws_icon}", ws_style),
                (" srt2web ", "bold cyan"),
                ("v0.6.8", "dim"),
                " │ ",
                (f"● {self.pipeline_state}", state_style),
                " │ ",
                (now, "dim"),
                " │ ",
                ("[Space] Start/Stop  [S]ave  [L]ogs  [I]nput  [P]reset  [R]ec  [?] Help", "dim"),
            )
        )
