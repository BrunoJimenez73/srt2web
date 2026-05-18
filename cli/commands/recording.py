from __future__ import annotations

import asyncio
import json

import click

from cli.client.http_client import APIClient


async def run_recording_list(api: APIClient, json_output: bool) -> int:
    """List all recordings."""
    try:
        recordings = await api.get_recordings()
    except Exception as e:
        click.echo(f"[red]Error fetching recordings:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(recordings, indent=2))
        return 0

    if not recordings:
        click.echo("No recordings found")
        return 0

    click.echo("Recordings:")
    for r in recordings:
        name = r.get("name", "unknown")
        size = r.get("size_formatted", "unknown size")
        fmt = r.get("format", "unknown format")
        modified = r.get("modified", "unknown date")
        click.echo(f"  {name} ({size}, {fmt}, modified: {modified})")
    return 0


async def run_recording_delete(api: APIClient, name: str, json_output: bool) -> int:
    """Delete a recording."""
    try:
        result = await api.delete_recording(name)
    except Exception as e:
        click.echo(f"[red]Error deleting recording:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Recording '{name}' deleted[/]")
    return 0


@click.group()
def recording() -> None:
    """Recording management commands."""


@recording.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def list(json_output: bool) -> None:
    """List all recordings."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_recording_list(api, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@recording.command()
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def delete(name: str, json_output: bool) -> None:
    """Delete a recording."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_recording_delete(api, name, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)
