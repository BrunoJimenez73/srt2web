from __future__ import annotations

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from cli.client.http_client import PipelineStatus


class TUIStatusBar(Static):
    def on_mount(self) -> None:
        self.update("Waiting for status...")

    def update_status(self, status: PipelineStatus) -> None:
        state_style = {
            "running": "bold green",
            "starting": "bold yellow",
            "stopping": "bold yellow",
            "stopped": "white",
            "error": "bold red",
            "idle": "dim white",
        }.get(status.state, "white")

        mode = status.mode or status.strategy or "—"

        uptime = ""
        if status.uptime_seconds:
            h, r = divmod(int(status.uptime_seconds), 3600)
            m, s = divmod(r, 60)
            uptime = f"{h}h {m:02d}m {s:02d}s"

        t = Text.assemble(
            (" State: ", "bold"),
            (f"● {status.state}", state_style),
            "\n",
            (" Chunks: ", "bold"),
            (f"{status.chunks_processed} processed", "green"),
            (" | ", "dim"),
            (f"{status.chunks_failed} failed", "red" if status.chunks_failed else "dim"),
            "\n",
            (" Mode: ", "bold"),
            (mode, "cyan"),
            "\n",
            (" Uptime: ", "bold"),
            (uptime or "—", "white"),
            "\n",
            (" Avg: ", "bold"),
            (f"{status.avg_processing_time_ms:.0f} ms" if status.avg_processing_time_ms else "—", "yellow"),
            (" | Concurrent: ", "bold"),
            (f"{status.concurrent_chunks}/{status.max_concurrent_chunks}", "white"),
        )
        self.update(t)
