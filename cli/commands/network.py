from __future__ import annotations

import json

import click

from cli.client.http_client import APIClient


async def run_network_info(api: APIClient, json_output: bool) -> int:
    """Get network information."""
    try:
        info = await api.get_network_info()
    except Exception as e:
        click.echo(f"[red]Error fetching network info:[/] {e}")
        return 1

    if json_output:
        # Convert NetworkInfo to dict for JSON output
        data = {
            "server_ip": info.server_ip,
            "server_port": info.server_port,
            "stream_url": info.stream_url,
            "player_url": info.player_url,
            "srt_url_listener": info.srt_url_listener,
            "srt_url_caller_template": info.srt_url_caller_template,
            "latency_ms": info.latency_ms,
            "srt_mode": info.srt_mode,
            "local_ip": info.local_ip,
            "public_ip": info.public_ip,
        }
        click.echo(json.dumps(data, indent=2))
        return 0

    click.echo("Network Information:")
    click.echo(f"  Server IP: {info.server_ip}")
    click.echo(f"  Server Port: {info.server_port}")
    click.echo(f"  Stream URL: {info.stream_url}")
    click.echo(f"  Player URL: {info.player_url}")
    click.echo(f"  SRT Listener URL: {info.srt_url_listener or '—'}")
    click.echo(f"  SRT Caller Template: {info.srt_url_caller_template or '—'}")
    click.echo(f"  Latency: {info.latency_ms} ms")
    click.echo(f"  SRT Mode: {info.srt_mode or '—'}")
    click.echo(f"  Local IP: {info.local_ip}")
    click.echo(f"  Public IP: {info.public_ip or '—'}")
    return 0


@click.group()
def network() -> None:
    """Network information commands."""


@network.command()
@click.option("-j", "--json", "json_output", is_flag=True, help="Output as JSON")
def info(json_output: bool) -> None:
    """Get network information."""
    import asyncio

    from cli.client.http_client import APIClient

    async def _run() -> int:
        api = APIClient()
        try:
            return await run_network_info(api, json_output)
        finally:
            await api.close()

    exit_code = asyncio.run(_run())
    raise SystemExit(exit_code)
