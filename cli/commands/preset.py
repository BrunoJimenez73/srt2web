from __future__ import annotations

import json

import click

from cli.client.http_client import APIClient


async def run_preset_list(api: APIClient, json_output: bool) -> int:
    """List all available presets."""
    try:
        presets = await api.get_presets()
    except Exception as e:
        click.echo(f"[red]Error fetching presets:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(presets, indent=2))
        return 0

    if not presets:
        click.echo("No presets found")
        return 0

    click.echo("Presets:")
    for p in presets:
        built_in = " (built-in)" if p.get("built_in") else ""
        desc = p.get("description", "No description")
        click.echo(f"  {p['name']}{built_in}: {desc}")
    return 0


async def run_preset_save(api: APIClient, name: str, description: str, json_output: bool) -> int:
    """Save current configuration as a preset."""
    try:
        result = await api.save_preset(name, description)
    except Exception as e:
        click.echo(f"[red]Error saving preset:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Preset '{name}' saved[/]")
    return 0


async def run_preset_apply(api: APIClient, name: str, json_output: bool) -> int:
    """Apply a preset."""
    try:
        result = await api.apply_preset(name)
    except Exception as e:
        click.echo(f"[red]Error applying preset:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Preset '{name}' applied[/]")
    return 0


async def run_preset_delete(api: APIClient, name: str, json_output: bool) -> int:
    """Delete a preset."""
    try:
        result = await api.delete_preset(name)
    except Exception as e:
        click.echo(f"[red]Error deleting preset:[/] {e}")
        return 1

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(f"[green]Preset '{name}' deleted[/]")
    return 0


@click.group()
def preset():
    """Preset management commands."""
    pass


@preset.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def list(json_output: bool):
    """List all available presets."""
    import asyncio

    from cli.client.http_client import APIClient

    async def _run():
        api = APIClient()
        try:
            return await run_preset_list(api, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@preset.command()
@click.argument("name")
@click.option("--description", default="", help="Description for the preset")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def save(name: str, description: str, json_output: bool):
    """Save current configuration as a preset."""
    import asyncio

    from cli.client.http_client import APIClient

    async def _run():
        api = APIClient()
        try:
            return await run_preset_save(api, name, description, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@preset.command()
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def apply(name: str, json_output: bool):
    """Apply a preset."""
    import asyncio

    from cli.client.http_client import APIClient

    async def _run():
        api = APIClient()
        try:
            return await run_preset_apply(api, name, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)


@preset.command()
@click.argument("name")
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def delete(name: str, json_output: bool):
    """Delete a preset."""
    import asyncio

    from cli.client.http_client import APIClient

    async def _run():
        api = APIClient()
        try:
            return await run_preset_delete(api, name, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)
