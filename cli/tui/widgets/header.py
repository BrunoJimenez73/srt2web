from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual.reactive import reactive
from textual.widgets import Static

from core.version import get_version


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
        from cli.constants import STATE_STYLE

        now = datetime.now().strftime("%H:%M:%S")
        base_style = STATE_STYLE.get(self.pipeline_state, "white")
        state_style = f"bold {base_style}" if base_style != "dim white" else base_style

        ws_icon = "●" if self.ws_connected else "○"
        ws_style = "green" if self.ws_connected else "red"

        self.update(
            Text.assemble(
                (f" {ws_icon}", ws_style),
                (" srt2web ", "bold cyan"),
                (f"v{get_version()}", "dim"),
                " │ ",
                (f"● {self.pipeline_state}", state_style),
                " │ ",
                (now, "dim"),
                " │ ",
                ("[Space] Start/Stop  [S]ave  [L]ogs  [I]nput  [P]reset  [R]ec  [?] Help", "dim"),
            )
        )
