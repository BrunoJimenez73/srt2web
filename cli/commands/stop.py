from __future__ import annotations

import json

from rich.console import Console

from cli.client.http_client import APIClient


async def run_stop(api: APIClient, console: Console, json_output: bool = False) -> int:
    try:
        result = await api.stop_pipeline()
    except Exception as e:
        console.print(f"[red]Error stopping pipeline:[/] {e}")
        return 1

    if json_output:
        console.print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")
        if status == "stopped":
            console.print("[green]✓ Pipeline stopped[/]")
        else:
            console.print(f"[yellow]Pipeline stop returned: {status}[/]")

    return 0
