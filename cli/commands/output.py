from __future__ import annotations

import asyncio
import json

import click

from cli.client.http_client import APIClient


async def run_output_list(api: APIClient, json_output: bool) -> int:
    """List all outputs with their status."""
    try:
        outputs = await api.get_outputs()
    except Exception as e:
        click.echo(f"[red]Error fetching outputs:[/] {e}")
        return 1

    if json_output:
        data = [
            {
                "name": o.name,
                "type": o.type,
                "state": o.state,
                "enabled": o.enabled,
                "processed_chunks": o.processed_chunks,
                "last_process_time_ms": o.last_process_time_ms,
                "stream_info": o.stream_info,
                "extra": o.extra,
            }
            for o in outputs
        ]
        click.echo(json.dumps(data, indent=2))
        return 0

    if not outputs:
        click.echo("No outputs found")
        return 0

    click.echo("Outputs:")
    for o in outputs:
        status_style = (
            "green"
            if o.state in ("running", "processing")
            else "yellow"
            if o.state in ("starting", "stopping", "initializing")
            else "red"
            if o.state == "error"
            else "white"
        )
        enabled_str = "[green]✓[/]" if o.enabled else "[red]✗[/]"
        click.echo(
            f"  {o.name} ({o.type}): [{status_style}]{o.state}[/] {enabled_str} "
            f"(chunks: {o.processed_chunks}, last: {o.last_process_time_ms:.0f}ms"
            f"{', stream: ' + str(o.stream_info) if o.stream_info else ''})"
        )
    return 0


async def run_output_add(
    api: APIClient, output_type: str, name: str | None, config: str | None, json_output: bool
) -> int:
    """Add a new output."""
    try:
        config_dict = json.loads(config) if config else None
    except json.JSONDecodeError as e:
        click.echo(f"[red]Invalid JSON config:[/] {e}")
        return 1

    try:
        result = await api.add_output(output_type, name, config_dict)
    except Exception as e:
        click.echo(f"[red]Error adding output:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Output '{result.get('name', 'unknown')}' added[/]")
    return 0


async def run_output_remove(api: APIClient, name: str, json_output: bool) -> int:
    """Remove an output."""
    try:
        result = await api.remove_output(name)
    except Exception as e:
        click.echo(f"[red]Error removing output:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Output '{name}' removed[/]")
    return 0


async def run_output_toggle(
    api: APIClient, name: str, enable: bool | None, disable: bool | None, json_output: bool
) -> int:
    """Enable or disable an output."""
    if enable is None and disable is None:
        # Toggle current state - need to get current status first
        try:
            outputs = await api.get_outputs()
            output = next((o for o in outputs if o.name == name), None)
            if not output:
                click.echo(f"[red]Output '{name}' not found[/]")
                return 1
            enabled = not output.enabled
        except Exception as e:
            click.echo(f"[red]Error fetching output status:[/] {e}")
            return 1
    else:
        enabled = bool(enable) if enable is not None else not bool(disable)

    try:
        result = await api.toggle_output(name, enabled)
    except Exception as e:
        click.echo(f"[red]Error toggling output:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        action = "enabled" if enabled else "disabled"
        click.echo(f"[green]Output '{name}' {action}[/]")
    return 0


async def run_output_update(
    api: APIClient, name: str, config: str | None, enable: bool | None, disable: bool | None, json_output: bool
) -> int:
    """Update an output's configuration or enabled state."""
    try:
        config_dict = json.loads(config) if config else None
    except json.JSONDecodeError as e:
        click.echo(f"[red]Invalid JSON config:[/] {e}")
        return 1

    try:
        result = await api.update_output(
            name,
            config_dict,
            bool(enable) if enable is not None else (not bool(disable) if disable is not None else None),
        )
    except Exception as e:
        click.echo(f"[red]Error updating output:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        updated_parts = []
        if config is not None:
            updated_parts.append("config")
        if enable is not None:
            updated_parts.append("enabled")
        if disable is not None:
            updated_parts.append("disabled")

        if updated_parts:
            click.echo(f"[green]Output '{name}' updated ({', '.join(updated_parts)})[/]")
        else:
            click.echo(f"[yellow]No changes specified for output '{name}'[/]")
    return 0


@click.group()
def output() -> None:
    """Output management commands."""


@output.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def list(json_output: bool) -> None:
    """List all outputs."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_output_list(api, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@output.command()
@click.argument("output_type")
@click.option("--name", help="Name for the output")
@click.option("--config", help="JSON configuration for the output")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def add(output_type: str, name: str | None, config: str | None, json_output: bool) -> None:
    """Add a new output."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_output_add(api, output_type, name, config, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@output.command()
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def remove(name: str, json_output: bool) -> None:
    """Remove an output."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_output_remove(api, name, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@output.command()
@click.argument("name")
@click.option("--enable", is_flag=True, help="Enable the output")
@click.option("--disable", is_flag=True, help="Disable the output")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def toggle(name: str, enable: bool, disable: bool, json_output: bool) -> None:
    """Enable or disable an output."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_output_toggle(api, name, enable, disable, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@output.command()
@click.argument("name")
@click.option("--config", help="JSON configuration for the output")
@click.option("--enable", is_flag=True, help="Enable the output")
@click.option("--disable", is_flag=True, help="Disable the output")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def update(name: str, config: str | None, enable: bool, disable: bool, json_output: bool) -> None:
    """Update an output's configuration or enabled state."""

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_output_update(api, name, config, enable, disable, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)
