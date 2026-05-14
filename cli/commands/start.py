from __future__ import annotations

import json

from rich.console import Console

from cli.client.http_client import APIClient


async def run_start(api: APIClient, console: Console, json_output: bool = False) -> int:
    try:
        result = await api.start_pipeline()
    except Exception as e:
        console.print(f"[red]Error starting pipeline:[/] {e}")
        return 1

    if json_output:
        console.print(json.dumps(result, indent=2))
    else:
        status = result.get("status", "unknown")
        if status == "started":
            console.print("[green]✓ Pipeline started successfully[/]")
        else:
            console.print(f"[yellow]Pipeline start returned: {status}[/]")

    return 0
