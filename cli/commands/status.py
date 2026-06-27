from __future__ import annotations

import json

from rich import box
from rich.console import Console
from rich.table import Table
from rich.text import Text

from cli.client.http_client import APIClient
from cli.constants import STATE_STYLE


def _state_style(state: str) -> str:
    return STATE_STYLE.get(state, "white")


def _state_label(state: str) -> Text:
    style = _state_style(state)
    if state in ("running", "processing"):
        return Text(f"● {state}", style=f"bold {style}")
    return Text(f"● {state}", style=style)


async def run_status(api: APIClient, console: Console, json_output: bool = False) -> int:
    try:
        status = await api.get_status()
    except Exception as e:
        console.print(f"[red]Error fetching status:[/] {e}")
        return 1

    if json_output:
        data = {
            "state": status.state,
            "mode": status.mode,
            "chunks_processed": status.chunks_processed,
            "chunks_failed": status.chunks_failed,
            "avg_processing_time_ms": status.avg_processing_time_ms,
            "uptime_seconds": status.uptime_seconds,
            "strategy": status.strategy,
            "modules": [
                {"name": m.get("name"), "state": m.get("state"), "enabled": m.get("enabled")} for m in status.modules
            ],
            "system": status.system,
        }
        console.print(json.dumps(data, indent=2))
        return 0

    table = Table(box=box.ROUNDED, title="Pipeline Status", title_style="bold cyan")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("State", _state_label(status.state))
    table.add_row("Mode", status.mode or status.strategy or "—")
    table.add_row("Chunks Processed", str(status.chunks_processed))
    table.add_row(
        "Chunks Failed", f"[red]{status.chunks_failed}[/]" if status.chunks_failed else str(status.chunks_failed)
    )
    table.add_row("Avg Processing", f"{status.avg_processing_time_ms:.0f} ms" if status.avg_processing_time_ms else "—")
    table.add_row("Uptime", f"{status.uptime_seconds:.0f}s" if status.uptime_seconds else "—")
    table.add_row("Concurrent", f"{status.concurrent_chunks}/{status.max_concurrent_chunks}")

    console.print(table)

    if status.system:
        sys_table = Table(box=box.ROUNDED, title="System Resources", title_style="bold cyan")
        sys_table.add_column("Resource", style="cyan")
        sys_table.add_column("Usage", style="white")

        cpu = status.system.get("cpu_percent", 0)
        mem_pct = status.system.get("memory_percent", 0)
        mem_mb = status.system.get("memory_mb", 0)
        gpu = status.system.get("gpu_util", 0)
        gpu_mem = status.system.get("gpu_memory_mb", 0)

        sys_table.add_row("CPU", f"{cpu:.1f}%" if cpu else "—")
        sys_table.add_row("Memory", f"{mem_mb:.0f} MB ({mem_pct:.1f}%)" if mem_mb else "—")
        sys_table.add_row("GPU", f"{gpu:.1f}%" if gpu else "N/A")
        sys_table.add_row("GPU Memory", f"{gpu_mem:.0f} MB" if gpu_mem else "N/A")
        console.print(sys_table)

    mod_table = Table(box=box.SIMPLE, title="Modules", title_style="bold cyan")
    mod_table.add_column("Module", style="cyan")
    mod_table.add_column("State", style="white")
    mod_table.add_column("Enabled", style="white")
    mod_table.add_column("Chunks", style="white")
    mod_table.add_column("Last (ms)", style="white")
    mod_table.add_column("Extra", style="dim")

    for m in status.modules:
        name = m.get("name", "?")
        state = m.get("state", "?")
        enabled = m.get("enabled", True)
        chunks = m.get("processed_chunks", 0)
        last = m.get("last_process_time_ms", 0)
        extra = m.get("extra", {})
        extra_str = ""
        if extra.get("using_gpu"):
            extra_str += "GPU "
        if extra.get("encoder_mode"):
            extra_str += extra["encoder_mode"]
        if extra.get("device"):
            extra_str += extra["device"]

        mod_table.add_row(
            name,
            _state_label(state),
            "✓" if enabled else "✗",
            str(chunks),
            f"{last:.0f}" if last else "—",
            extra_str.strip(),
        )

    console.print(mod_table)
    return 0
