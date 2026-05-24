from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.tree import Tree

from cli.client.http_client import APIClient


def _build_tree(data: Any, tree: Tree | None = None, key: str = "") -> Tree:
    if tree is None:
        tree = Tree(f"[bold cyan]{key}[/]" if key else "[bold]Config[/]")
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, dict):
                branch = tree.add(f"[cyan]{k}[/]")
                _build_tree(v, branch)
            elif isinstance(v, list):
                branch = tree.add(f"[cyan]{k}[/] [dim]({len(v)} items)[/]")
                for i, item in enumerate(v):
                    if isinstance(item, dict):
                        sub = branch.add(f"[dim]{i}[/]")
                        _build_tree(item, sub)
                    else:
                        branch.add(f"[dim]{i}:[/] {_format_value(item)}")
            else:
                tree.add(f"[cyan]{k}:[/] {_format_value(v)}")
    return tree


def _format_value(v: Any) -> str:
    if v is None:
        return "[dim]null[/]"
    if isinstance(v, bool):
        return f"[green]{v}[/]"
    if isinstance(v, int | float):
        return f"[yellow]{v}[/]"
    if isinstance(v, str):
        if not v:
            return '[dim]""[/]'
        return f'[white]"{v}"[/]'
    return str(v)


async def run_config_get(api: APIClient, console: Console, key: str | None = None, json_output: bool = False) -> int:
    try:
        config = await api.get_config()
    except Exception as e:
        console.print(f"[red]Error fetching config:[/] {e}")
        return 1

    if key:
        val = config.get(key)
        if val is None:
            console.print(f"[yellow]Key '{key}' not found[/]")
            return 1
        if json_output:
            console.print(json.dumps(val, indent=2))
        else:
            console.print(_format_value(val))
        return 0

    if json_output:
        console.print(json.dumps(config.raw, indent=2))
    else:
        tree = _build_tree(config.raw)
        console.print(tree)

    return 0


async def run_config_set(api: APIClient, console: Console, key: str, value: str, json_output: bool = False) -> int:
    try:
        config = await api.get_config()
    except Exception as e:
        console.print(f"[red]Error fetching config:[/] {e}")
        return 1

    parsed: Any
    if value.lower() == "true":
        parsed = True
    elif value.lower() == "false":
        parsed = False
    elif value.lower() == "null":
        parsed = None
    else:
        try:
            parsed = int(value)
        except ValueError:
            try:
                parsed = float(value)
            except ValueError:
                parsed = value

    config.set(key, parsed)

    try:
        result = await api.update_config(config.raw)
    except Exception as e:
        console.print(f"[red]Error updating config:[/] {e}")
        return 1

    if json_output:
        console.print(json.dumps(result, indent=2))
    else:
        console.print(f"[green]✓[/] [cyan]{key}[/] set to {_format_value(parsed)}")

    return 0


async def run_config_show(api: APIClient, console: Console, json_output: bool = False) -> int:
    return await run_config_get(api, console, key=None, json_output=json_output)
