from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.widgets import Static


def _bar(value: float, max_val: float = 100, width: int = 20) -> str:
    filled = int((value / max_val) * width) if max_val > 0 else 0
    filled = min(filled, width)
    empty = width - filled
    blocks = "█" * filled + "░" * empty
    pct = f"{value:.1f}%" if max_val == 100 else f"{value:.0f}"
    return f"{blocks} {pct}"


def _sparkline(values: list[float], width: int = 10) -> str:
    if not values:
        return "─" * width
    max_v = max(values) or 1
    chars = []
    for v in values[-width:]:
        ratio = v / max_v
        if ratio > 0.9:
            chars.append("▇")
        elif ratio > 0.7:
            chars.append("▆")
        elif ratio > 0.5:
            chars.append("▅")
        elif ratio > 0.3:
            chars.append("▃")
        elif ratio > 0.1:
            chars.append("▂")
        else:
            chars.append("▁")
    return "".join(chars).rjust(width, "─")


class TUIMetricsPanel(Static):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._cpu_history: list[float] = []
        self._gpu_history: list[float] = []

    def on_mount(self) -> None:
        self._show_idle()

    def _show_idle(self) -> None:
        t = Text.assemble(
            (" CPU:     ", "bold"),
            ("─" * 22, "dim"),
            "\n",
            (" Memory:  ", "bold"),
            ("─" * 22, "dim"),
            "\n",
            (" GPU:     ", "bold"),
            ("─" * 22, "dim"),
            "\n",
            (" Throughput: ", "bold"),
            ("─" * 22, "dim"),
        )
        self.update(t)

    def update_metrics(self, system: dict[str, Any]) -> None:
        if not system:
            self._show_idle()
            return

        cpu = system.get("cpu_percent", 0)
        mem_mb = system.get("memory_mb", 0)
        mem_pct = system.get("memory_percent", 0)
        gpu = system.get("gpu_util", 0)
        gpu_mem = system.get("gpu_memory_mb", 0)
        throughput = system.get("throughput", 0)
        latency = system.get("latency_ms", 0)

        self._cpu_history.append(cpu)
        if len(self._cpu_history) > 20:
            self._cpu_history = self._cpu_history[-20:]
        self._gpu_history.append(gpu)
        if len(self._gpu_history) > 20:
            self._gpu_history = self._gpu_history[-20:]

        cpu_bar = _bar(float(cpu))
        mem_bar = _bar(float(mem_pct))
        gpu_bar = _bar(float(gpu))
        thr_bar = _bar(float(throughput), max_val=max(throughput + 1, 10))
        cpu_spark = _sparkline(self._cpu_history)
        gpu_spark = _sparkline(self._gpu_history)

        t = Text.assemble(
            (" CPU:     ", "bold"),
            (cpu_bar, "green"),
            (" ", "dim"),
            (cpu_spark, "dim"),
            "\n",
            (" Memory:  ", "bold"),
            (mem_bar, "cyan"),
            (" ", "dim"),
            (f"{mem_mb:.0f} MB", "dim"),
            "\n",
            (" GPU:     ", "bold"),
            (gpu_bar, "magenta"),
            (" ", "dim"),
            (gpu_spark, "dim"),
            (" | " if gpu_mem else "", "dim"),
            (f"{gpu_mem:.0f} MB" if gpu_mem else "", "dim"),
            "\n",
            (" Throughput: ", "bold"),
            (thr_bar, "yellow"),
            (" | Latency: ", "dim"),
            (f"{latency:.0f} ms" if latency else "—", "yellow" if latency else "dim"),
        )
        self.update(t)
