from __future__ import annotations

import asyncio

from rich.console import Console
from rich.table import Table
from rich.text import Text

from cli.client.http_client import LogEntry
from cli.client.ws_client import WSClient


def _level_style(level: str) -> str:
    return {
        "INFO": "green",
        "WARNING": "yellow",
        "WARN": "yellow",
        "ERROR": "red",
        "CRITICAL": "red bold",
        "DEBUG": "dim blue",
    }.get(level.upper(), "white")


def _format_log(entry: LogEntry) -> Text:
    time_str = entry.time_str or ""
    level_str = entry.level.ljust(8)
    t = Text()
    t.append(time_str, style="dim")
    t.append(" | ")
    t.append(level_str, style=_level_style(entry.level))
    t.append(" | ")
    t.append(entry.message)
    return t


async def run_logs(
    api_base: str,
    token: str | None,
    console: Console,
    level_filter: str | None = None,
    follow: bool = True,
    tail_lines: int = 50,
) -> int:
    buffer: list[LogEntry] = []

    def on_log(entry: LogEntry) -> None:
        if level_filter and entry.level.upper() != level_filter.upper():
            return
        buffer.append(entry)

    ws = WSClient(url=api_base, token=token, on_log=on_log)
    await ws.connect()

    try:
        if follow:
            console.print("[dim]Listening for logs... (Ctrl+C to stop)[/]")
            while True:
                while buffer:
                    entry = buffer.pop(0)
                    console.print(_format_log(entry))
                await asyncio.sleep(0.1)
        else:
            await asyncio.sleep(2)
            await ws.disconnect()
            if not buffer:
                console.print("[yellow]No log entries received.[/]")
                return 0
            table = Table(box=None)
            table.add_column("Time", style="dim", no_wrap=True)
            table.add_column("Level", no_wrap=True)
            table.add_column("Message")
            for entry in buffer[-tail_lines:]:
                if level_filter and entry.level.upper() != level_filter.upper():
                    continue
                table.add_row(
                    Text(entry.time_str, style="dim"),
                    Text(entry.level, style=_level_style(entry.level)),
                    Text(entry.message),
                )
            console.print(table)

    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    finally:
        await ws.disconnect()

    return 0
