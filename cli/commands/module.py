from __future__ import annotations

import asyncio
import json

import click

from cli.client.http_client import APIClient


async def run_module_list(api: APIClient, json_output: bool) -> int:
    """List all modules with their status."""
    try:
        modules = await api.get_modules()
    except Exception as e:
        click.echo(f"[red]Error fetching modules:[/] {e}")
        return 1

    if json_output:
        data = [
            {
                "name": m.name,
                "state": m.state,
                "enabled": m.enabled,
                "processed_chunks": m.processed_chunks,
                "last_process_time_ms": m.last_process_time_ms,
                "memory_mb": m.memory_mb,
                "extra": m.extra,
            }
            for m in modules
        ]
        click.echo(json.dumps(data, indent=2))
        return 0

    if not modules:
        click.echo("No modules found")
        return 0

    click.echo("Modules:")
    for m in modules:
        status_style = (
            "green"
            if m.state in ("running", "processing")
            else "yellow"
            if m.state in ("starting", "stopping", "initializing")
            else "red"
            if m.state == "error"
            else "white"
        )
        enabled_str = "[green]✓[/]" if m.enabled else "[red]✗[/]"
        click.echo(
            f"  {m.name}: [{status_style}]{m.state}[/] {enabled_str} "
            f"(chunks: {m.processed_chunks}, last: {m.last_process_time_ms:.0f}ms"
            f"{', GPU: ' + str(m.memory_mb) + 'MB' if m.memory_mb > 0 else ''})"
        )
    return 0


async def run_module_toggle(
    api: APIClient, name: str, enable: bool | None, disable: bool | None, json_output: bool
) -> int:
    """Enable or disable a module."""
    if enable is None and disable is None:
        # Toggle current state
        try:
            modules = await api.get_modules()
            module = next((m for m in modules if m.name == name), None)
            if not module:
                click.echo(f"[red]Module '{name}' not found[/]")
                return 1
            enabled = not module.enabled
        except Exception as e:
            click.echo(f"[red]Error fetching module status:[/] {e}")
            return 1
    else:
        enabled = bool(enable) if enable is not None else not bool(disable)

    try:
        result = await api.toggle_module(name, enabled)
    except Exception as e:
        click.echo(f"[red]Error toggling module:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        action = "enabled" if enabled else "disabled"
        click.echo(f"[green]Module '{name}' {action}[/]")
    return 0


async def run_module_debug(api: APIClient, name: str, json_output: bool) -> int:
    """Get debug information for a module."""
    try:
        data = await api.get_module_debug(name)
    except Exception as e:
        click.echo(f"[red]Error fetching module debug:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(data, indent=2))
    else:
        click.echo(f"Debug info for module '{name}':")
        for key, value in data.items():
            click.echo(f"  {key}: {value}")
    return 0


@click.group()
def module() -> None:
    """Module management commands."""


@module.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def list(json_output: bool) -> None:
    """List all modules."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_module_list(api, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@module.command()
@click.argument("name")
@click.option("--enable", is_flag=True, help="Enable the module")
@click.option("--disable", is_flag=True, help="Disable the module")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def toggle(name: str, enable: bool, disable: bool, json_output: bool) -> None:
    """Enable or disable a module."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_module_toggle(api, name, enable, disable, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@module.command()
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def debug(name: str, json_output: bool) -> None:
    """Get debug information for a module."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_module_debug(api, name, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)
