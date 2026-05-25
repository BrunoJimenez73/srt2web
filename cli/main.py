from __future__ import annotations

import asyncio
import logging
import sys

import click
import colorama  # type: ignore[import-untyped]
from rich.console import Console

from cli.client.http_client import DEFAULT_SERVER, APIClient
from cli.commands.input import input as input_cmd_group
from cli.commands.module import module as module_group
from cli.commands.network import network as network_group
from cli.commands.output import output as output_group
from cli.commands.preset import preset as preset_group
from cli.commands.recording import recording as recording_group
from core.version import get_version

logger = logging.getLogger("srt2web.cli")

colorama.init()

# Fix Windows console encoding for Unicode chars
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception as e:
        logger.debug("Could not reconfigure stdout encoding: %s", e)
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception as e:
        logger.debug("Could not reconfigure stderr encoding: %s", e)


@click.group(invoke_without_command=True)
@click.option("--server", "-s", default=DEFAULT_SERVER, help="Server base URL (default: http://localhost:9999)")
@click.option("--token", "-t", default=None, help="Auth token for protected servers")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.version_option(version=get_version(), prog_name="srt2web-tui")
@click.pass_context
def cli(ctx: click.Context, server: str, token: str | None, json_output: bool) -> None:
    """srt2web CLI + TUI — Monitor and control the srt2web pipeline from the terminal."""
    ctx.ensure_object(dict)
    ctx.obj["server"] = server
    ctx.obj["token"] = token
    ctx.obj["json"] = json_output

    if ctx.invoked_subcommand is None:
        # Default: launch TUI
        from cli.tui.app import run_tui

        run_tui(server=server, token=token)


@cli.command()
@click.argument("action", type=click.Choice(["start", "stop", "restart"]))
@click.pass_context
def pipeline(ctx: click.Context, action: str) -> None:
    """Control the pipeline: start, stop, or restart."""

    async def _run() -> int:
        api = APIClient(ctx.obj["server"], ctx.obj["token"])
        console = Console()
        try:
            if action == "start":
                from cli.commands.start import run_start

                return await run_start(api, console, ctx.obj["json"])
            if action == "stop":
                from cli.commands.stop import run_stop

                return await run_stop(api, console, ctx.obj["json"])
            if action == "restart":
                result = await api.restart_pipeline()
                if ctx.obj["json"]:
                    import json

                    console.print(json.dumps(result, indent=2))
                else:
                    console.print("[green]✓ Pipeline restarted[/]")
                return 0
            return 1
        finally:
            await api.close()

    sys.exit(asyncio.run(_run()))


@cli.command()
@click.argument("key", required=False, default=None)
@click.argument("value", required=False, default=None)
@click.pass_context
def config(ctx: click.Context, key: str | None, value: str | None) -> None:
    """View or modify pipeline configuration.

    Usage: config [KEY] [VALUE]

    Without arguments, shows the full configuration tree.
    With KEY, shows the value at that dotted path (e.g. server.port).
    With KEY and VALUE, sets the configuration parameter.
    """

    async def _run() -> int:
        api = APIClient(ctx.obj["server"], ctx.obj["token"])
        console = Console()
        try:
            if key and value:
                from cli.commands.config import run_config_set

                return await run_config_set(api, console, key, value, ctx.obj["json"])
            elif key:
                from cli.commands.config import run_config_get

                return await run_config_get(api, console, key, ctx.obj["json"])
            else:
                from cli.commands.config import run_config_show

                return await run_config_show(api, console, ctx.obj["json"])
        finally:
            await api.close()

    sys.exit(asyncio.run(_run()))


@cli.command()
@click.option("--follow", "-f", is_flag=True, default=True, help="Follow log output (default: True)")
@click.option("--no-follow", is_flag=True, help="Print existing logs and exit")
@click.option("--level", "-l", default=None, help="Filter by level: INFO, WARNING, ERROR")
@click.option("--tail", default=50, help="Number of lines to show (default: 50)")
@click.pass_context
def logs(ctx: click.Context, follow: bool, no_follow: bool, level: str | None, tail: int) -> None:
    """View pipeline logs in real-time."""
    from cli.commands.logs import run_logs

    sys.exit(
        asyncio.run(
            run_logs(
                api_base=ctx.obj["server"],
                token=ctx.obj["token"],
                console=Console(),
                level_filter=level,
                follow=follow and not no_follow,
                tail_lines=tail,
            )
        )
    )


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show pipeline status, modules, and system resources."""

    async def _run() -> int:
        api = APIClient(ctx.obj["server"], ctx.obj["token"])
        console = Console()
        try:
            from cli.commands.status import run_status

            return await run_status(api, console, ctx.obj["json"])
        finally:
            await api.close()

    sys.exit(asyncio.run(_run()))


@cli.command()
@click.pass_context
def tui(ctx: click.Context) -> None:
    """Launch the interactive terminal UI (default)."""
    from cli.tui.app import run_tui

    run_tui(server=ctx.obj["server"], token=ctx.obj["token"])


@cli.command()
@click.pass_context
def health(ctx: click.Context) -> None:
    """Show detailed system health."""

    async def _run() -> int:
        api = APIClient(ctx.obj["server"], ctx.obj["token"])
        console = Console()
        try:
            health_info = await api.get_health()
            if ctx.obj["json"]:
                import json
                from dataclasses import asdict

                console.print(json.dumps(asdict(health_info), indent=2))
            else:
                console.print(f"Status: [green]{health_info.status}[/]")
                console.print(f"Pipeline: {health_info.pipeline_state}")
                console.print(f"Uptime: {health_info.uptime_seconds:.0f}s")
                console.print(f"Memory: {health_info.memory_mb:.0f} MB ({health_info.memory_percent:.1f}%)")
                console.print(f"Chunks: {health_info.chunks_processed}")
            return 0
        finally:
            await api.close()

    sys.exit(asyncio.run(_run()))


# Register command groups as sub-groups
cli.add_command(module_group)
cli.add_command(output_group)
cli.add_command(preset_group)
cli.add_command(recording_group)
cli.add_command(input_cmd_group)
cli.add_command(network_group)


def cli_entry() -> None:
    cli(obj={})


if __name__ == "__main__":
    cli_entry()
