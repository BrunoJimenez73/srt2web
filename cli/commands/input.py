from __future__ import annotations

import asyncio
import json

import click

from cli.client.http_client import APIClient


async def run_input_info(api: APIClient, json_output: bool) -> int:
    """Get information about the current input."""
    try:
        info = await api.get_input_info()
    except Exception as e:
        click.echo(f"[red]Error fetching input info:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(info, indent=2))
        return 0

    if not info:
        click.echo("No input connected")
        return 0

    click.echo("Input Information:")
    for key, value in info.items():
        click.echo(f"  {key}: {value}")
    return 0


async def run_input_control(api: APIClient, action: str, value: float | None, json_output: bool) -> int:
    """Control input playback (play, pause, seek)."""
    try:
        data = {"position": value} if value is not None else None
        result = await api.control_input(action, data)
    except Exception as e:
        click.echo(f"[red]Error controlling input:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Input {action} successful[/]")
        if value is not None:
            click.echo(f"  Position: {value}s")
    return 0


@click.group()
def input() -> None:
    """Input control commands."""


@input.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def info(json_output: bool) -> None:
    """Get information about the current input."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_input_info(api, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@input.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def play(json_output: bool) -> None:
    """Start or resume input playback."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_input_control(api, "play", None, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@input.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def pause(json_output: bool) -> None:
    """Pause input playback."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_input_control(api, "pause", None, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@input.command()
@click.argument("position", type=float)
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def seek(position: float, json_output: bool) -> None:
    """Seek to a specific position in seconds."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_input_control(api, "seek", position, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)
