#!/usr/bin/env python3
"""
SRT2Web CLI - Control SRT2Web server from command line.

Usage:
    python srt2web.py status
    python srt2web.py start
    python srt2web.py config get
    python srt2web.py modules list
    python srt2web.py logs --tail 50

For interactive watch mode:
    python srt2web.py status --watch
"""

import argparse
import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import Optional, Any

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    import urllib.request
    import urllib.error
    import urllib.parse

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    import colorama
    colorama.init(autoreset=True)
    RESET = colorama.Fore.RESET
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    CYAN = colorama.Fore.CYAN
    MAGENTA = colorama.Fore.MAGENTA
    DIM = colorama.Fore.LIGHTBLACK_EX
except ImportError:
    RESET = GREEN = RED = YELLOW = CYAN = MAGENTA = DIM = ""


API_BASE = "http://localhost:9999/api"
WS_URL = "ws://localhost:9999/ws/logs"
CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"


def get_token() -> Optional[str]:
    """Get auth token from config."""
    if not HAS_YAML:
        return None
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE) as f:
                config = yaml.safe_load(f)
            return config.get("server", {}).get("auth_token", "")
    except Exception:
        pass
    return None


def get_headers() -> dict:
    """Get HTTP headers with auth if configured."""
    token = get_token()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def api_request(method: str, path: str, data: Any = None, params: dict = None) -> dict:
    """Make API request."""
    url = f"{API_BASE}{path}"
    headers = get_headers()
    headers["Content-Type"] = "application/json"

    try:
        if HAS_REQUESTS:
            if method == "GET":
                r = requests.get(url, headers=headers, params=params, timeout=10)
            elif method == "POST":
                r = requests.post(url, headers=headers, json=data, timeout=10)
            elif method == "PUT":
                r = requests.put(url, headers=headers, json=data, timeout=10)
            elif method == "DELETE":
                r = requests.delete(url, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unknown method: {method}")
            r.raise_for_status()
            return r.json() if r.content else {}
        else:
            body = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            if params:
                req.full_url = url + "?" + urllib.parse.urlencode(params)
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}")
        sys.exit(1)


def print_status(status: dict, watch: bool = False):
    """Print pipeline status in human-readable format."""
    state = status.get("state", "unknown")
    chunks = status.get("chunks_processed", 0)

    state_color = GREEN if state == "running" else RED if state == "error" else YELLOW
    print(f"\n{CYAN}=== SRT2Web Status ==={RESET}")
    print(f"  State:    {state_color}{state.upper()}{RESET}")
    print(f"  Chunks:   {chunks}")

    modules = status.get("modules", [])
    if modules:
        print(f"\n{CYAN}Modules:{RESET}")
        for m in modules:
            m_name = m.get("name", "?")
            m_state = m.get("state", "unknown")
            m_chunks = m.get("processed_chunks", 0)
            m_time = m.get("last_process_time_ms", 0)
            m_enabled = m.get("enabled", True)
            error = m.get("error_message")

            m_color = GREEN if m_state == "running" and m_enabled else RED if not m_enabled else YELLOW
            status_str = f"{m_color}{m_state}{RESET}" if m_enabled else f"{DIM}disabled{RESET}"
            time_str = f"{m_time:.1f}ms" if m_time else "-"

            print(f"  {m_name:20} {status_str:12} {m_chunks:5} chunks  {time_str:>8}  {error or ''}")

    network = status.get("network", {})
    if network:
        print(f"\n{CYAN}Network:{RESET}")
        print(f"  SRT:     {network.get('srt_port', '-')}")
        print(f"  Mode:    {network.get('srt_mode', '-')}")

    print()


def print_health(health: dict):
    """Print health check in human-readable format."""
    status = health.get("status", "unknown")
    uptime = health.get("uptime_seconds", 0)
    memory = health.get("memory_mb", 0)
    chunks = health.get("chunks_processed", 0)

    status_color = GREEN if status == "healthy" else YELLOW if status == "degraded" else RED
    print(f"\n{CYAN}=== Health Check ==={RESET}")
    print(f"  Status:   {status_color}{status.upper()}{RESET}")
    print(f"  Uptime:   {uptime:.0f}s")
    print(f"  Memory:   {memory:.1f} MB")
    print(f"  Chunks:   {chunks}")
    print()


def print_config(config: dict, key: Optional[str] = None):
    """Print configuration."""
    if key:
        keys = key.split(".")
        val = config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                val = None
                break
        print(f"{key} = {val}")
        return

    print(f"\n{CYAN}=== Configuration ==={RESET}")
    print(json.dumps(config, indent=2))
    print()


def print_modules(modules: list):
    """Print module list."""
    print(f"\n{CYAN}=== Modules ==={RESET}")
    for m in modules:
        name = m.get("name", "?")
        state = m.get("state", "unknown")
        enabled = m.get("enabled", True)
        chunks = m.get("processed_chunks", 0)
        error = m.get("error_message")

        state_color = GREEN if state == "running" and enabled else RED if not enabled else YELLOW
        print(f"  {name:20} {state_color}{state}{RESET}  {chunks:5} chunks")
        if error:
            print(f"    {RED}Error: {error}{RESET}")
    print()


def print_outputs(outputs: list):
    """Print output list."""
    print(f"\n{CYAN}=== Outputs ==={RESET}")
    for o in outputs:
        name = o.get("name", "?")
        o_type = o.get("type", "?")
        state = o.get("state", "unknown")
        enabled = o.get("enabled", True)
        chunks = o.get("processed_chunks", 0)

        state_color = GREEN if state == "running" and enabled else RED if not enabled else YELLOW
        print(f"  {name:25} {o_type:10} {state_color}{state}{RESET}  {chunks:5} chunks")
    print()


def cmd_status(args):
    """Handle status command."""
    if args.watch:
        print(f"{YELLOW}Watching status (Ctrl+C to exit)...{RESET}")
        try:
            while True:
                status = api_request("GET", "/status")
                os.system("cls" if os.name == "nt" else "clear")
                print_status(status, watch=True)
                time.sleep(2)
        except KeyboardInterrupt:
            print(f"\n{DIM}Stopped watching.{RESET}")
    else:
        status = api_request("GET", "/status")
        print_status(status)


def cmd_health(args):
    """Handle health command."""
    health = api_request("GET", "/health")
    print_health(health)


def cmd_start(args):
    """Handle start command."""
    print(f"{GREEN}Starting pipeline...{RESET}")
    result = api_request("POST", "/start")
    print(f"{GREEN}Pipeline started: {result.get('status')}{RESET}")


def cmd_stop(args):
    """Handle stop command."""
    print(f"{YELLOW}Stopping pipeline...{RESET}")
    result = api_request("POST", "/stop")
    print(f"{GREEN}Pipeline stopped: {result.get('status')}{RESET}")


def cmd_restart(args):
    """Handle restart command."""
    print(f"{YELLOW}Restarting pipeline...{RESET}")
    result = api_request("POST", "/restart")
    print(f"{GREEN}Pipeline restarted: {result.get('status')}{RESET}")


def cmd_config(args):
    """Handle config commands."""
    if args.config_action == "get":
        config = api_request("GET", "/config")
        print_config(config, args.key)
    elif args.config_action == "set":
        updates = {}
        for kv in args.set:
            if "=" not in kv:
                print(f"{RED}Invalid format: {kv} (use key=value){RESET}")
                sys.exit(1)
            key, value = kv.split("=", 1)
            keys = key.split(".")
            d = updates
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            try:
                d[keys[-1]] = json.loads(value)
            except json.JSONDecodeError:
                d[keys[-1]] = value
        result = api_request("PUT", "/config", data={"config": updates})
        print(f"{GREEN}Config updated{RESET}")
    elif args.config_action == "save":
        config = api_request("GET", "/config")
        if not HAS_YAML:
            print(f"{RED}PyYAML not installed, cannot save to file{RESET}")
            sys.exit(1)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        print(f"{GREEN}Config saved to {CONFIG_FILE}{RESET}")


def cmd_modules(args):
    """Handle module commands."""
    if args.module_action == "list":
        result = api_request("GET", "/modules")
        print_modules(result.get("modules", []))
    elif args.module_action == "toggle":
        result = api_request("PUT", f"/modules/{args.name}/toggle", data={"enabled": args.enable})
        print(f"{GREEN}Module {args.name}: {'enabled' if args.enable else 'disabled'}{RESET}")
    elif args.module_action == "debug":
        result = api_request("GET", f"/modules/{args.name}/debug")
        print(json.dumps(result, indent=2))


def cmd_outputs(args):
    """Handle output commands."""
    if args.output_action == "list":
        result = api_request("GET", "/outputs")
        print_outputs(result.get("outputs", []))
    elif args.output_action == "add":
        output_config = {"type": args.type}
        if args.output_name:
            output_config["name"] = args.output_name
        if args.output_config:
            output_config["config"] = {}
            for kv in args.output_config:
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    try:
                        output_config["config"][k] = json.loads(v)
                    except json.JSONDecodeError:
                        output_config["config"][k] = v
        result = api_request("POST", "/outputs", data=output_config)
        print(f"{GREEN}Output added: {result.get('name')} ({result.get('type')}){RESET}")
    elif args.output_action == "remove":
        result = api_request("DELETE", f"/outputs/{args.name}")
        print(f"{GREEN}Output removed: {args.name}{RESET}")
    elif args.output_action == "toggle":
        result = api_request("POST", f"/outputs/{args.name}/toggle")
        enabled = result.get("enabled", False)
        print(f"{GREEN}Output {args.name}: {'enabled' if enabled else 'disabled'}{RESET}")


def cmd_logs(args):
    """Handle logs command."""
    limit = args.tail or 50
    offset = args.offset or 0
    filter_level = args.filter

    logs = api_request("GET", "/logs", params={"limit": limit, "offset": offset, "level": filter_level})

    print(f"\n{CYAN}=== Logs (last {limit}) ==={RESET}")
    for log in logs.get("logs", []):
        level = log.get("level", "info")
        msg = log.get("message", "")
        ts = log.get("timestamp", "")

        level_color = {
            "error": RED,
            "warning": YELLOW,
            "info": GREEN,
            "debug": DIM,
        }.get(level, "")

        print(f"{DIM}{ts:>12}{RESET} {level_color}{level:8}{RESET} {msg}")

    print()


def cmd_stream(args):
    """Open stream in browser."""
    import webbrowser
    url = f"http://localhost:9999/player"
    print(f"{CYAN}Opening {url}...{RESET}")
    webbrowser.open(url)


def cmd_available(args):
    """Show available input/output types."""
    result = api_request("GET", "/available")
    print(f"\n{CYAN}=== Available Types ==={RESET}")
    print(f"  Inputs:  {', '.join(result.get('inputs', []))}")
    print(f"  Outputs: {', '.join(result.get('outputs', []))}")
    print()


def cmd_shell(args):
    """Interactive shell mode."""
    print(f"""
{CYAN}=== SRT2Web Interactive Shell ===
Commands: status, start, stop, health, modules, outputs, logs, config, exit
Type 'help' for more info.{RESET}
""")

    while True:
        try:
            cmd = input(f"{GREEN}srt2web>{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not cmd:
            continue
        if cmd in ("exit", "quit", "q"):
            break

        parts = cmd.split()
        subcmd = parts[0] if parts else ""

        try:
            if subcmd == "status":
                status = api_request("GET", "/status")
                print_status(status)
            elif subcmd == "health":
                health = api_request("GET", "/health")
                print_health(health)
            elif subcmd == "start":
                api_request("POST", "/start")
                print(f"{GREEN}Started{RESET}")
            elif subcmd == "stop":
                api_request("POST", "/stop")
                print(f"{GREEN}Stopped{RESET}")
            elif subcmd == "modules":
                result = api_request("GET", "/modules")
                print_modules(result.get("modules", []))
            elif subcmd == "outputs":
                result = api_request("GET", "/outputs")
                print_outputs(result.get("outputs", []))
            elif subcmd == "logs":
                logs = api_request("GET", "/logs", params={"limit": 20})
                for log in logs.get("logs", []):
                    print(f"{log.get('level', 'info'):8} {log.get('message', '')}")
            elif subcmd == "config":
                config = api_request("GET", "/config")
                print(json.dumps(config, indent=2))
            elif subcmd in ("help", "?"):
                print("""
Commands:
  status, health    - Show status/health
  start, stop      - Control pipeline
  modules          - List modules
  outputs          - List outputs
  logs [n]         - Show last n logs
  config           - Show config
  exit             - Exit shell
                """)
            else:
                print(f"{RED}Unknown command: {subcmd}{RESET}")
        except Exception as e:
            print(f"{RED}Error: {e}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="SRT2Web CLI - Control SRT2Web server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # status
    status_parser = subparsers.add_parser("status", help="Show pipeline status")
    status_parser.add_argument("--watch", "-w", action="store_true", help="Watch mode (Ctrl+C to exit)")

    # health
    subparsers.add_parser("health", help="Show health check")

    # start/stop/restart
    subparsers.add_parser("start", help="Start pipeline")
    subparsers.add_parser("stop", help="Stop pipeline")
    subparsers.add_parser("restart", help="Restart pipeline")

    # config
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_subparsers = config_parser.add_subparsers(dest="config_action", help="Config action")
    config_get = config_subparsers.add_parser("get", help="Get config")
    config_get.add_argument("key", nargs="?", help="Config key (e.g., pipeline.chunk_duration_sec)")
    config_set = config_subparsers.add_parser("set", help="Set config value")
    config_set.add_argument("set", nargs="+", help="key=value pairs")
    config_subparsers.add_parser("save", help="Save config to file")

    # modules
    module_parser = subparsers.add_parser("modules", help="Module management")
    module_subparsers = module_parser.add_subparsers(dest="module_action", help="Module action")
    module_list = module_subparsers.add_parser("list", help="List modules")
    module_toggle = module_subparsers.add_parser("toggle", help="Toggle module")
    module_toggle.add_argument("name", help="Module name")
    module_toggle.add_argument("--enable", type=bool, help="True to enable, False to disable")
    module_debug = module_subparsers.add_parser("debug", help="Debug module")
    module_debug.add_argument("name", help="Module name")

    # outputs
    output_parser = subparsers.add_parser("outputs", help="Output management")
    output_subparsers = output_parser.add_subparsers(dest="output_action", help="Output action")
    output_list = output_subparsers.add_parser("list", help="List outputs")
    output_add = output_subparsers.add_parser("add", help="Add output")
    output_add.add_argument("type", help="Output type (web, recording, rtmp, srt, file)")
    output_add.add_argument("--name", help="Output name")
    output_add.add_argument("--config", nargs="+", help="key=value config options")
    output_rm = output_subparsers.add_parser("remove", help="Remove output")
    output_rm.add_argument("name", help="Output name")
    output_toggle = output_subparsers.add_parser("toggle", help="Toggle output")
    output_toggle.add_argument("name", help="Output name")

    # logs
    logs_parser = subparsers.add_parser("logs", help="Show logs")
    logs_parser.add_argument("--tail", "-n", type=int, help="Number of logs to show")
    logs_parser.add_argument("--offset", type=int, help="Log offset")
    logs_parser.add_argument("--filter", "-f", help="Filter by level (error, warning, info)")

    # stream
    subparsers.add_parser("stream", help="Open stream player in browser")

    # available
    subparsers.add_parser("available", help="Show available input/output types")

    # shell
    subparsers.add_parser("shell", help="Interactive shell mode")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "status": cmd_status,
        "health": cmd_health,
        "start": cmd_start,
        "stop": cmd_stop,
        "restart": cmd_restart,
        "config": cmd_config,
        "modules": cmd_modules,
        "outputs": cmd_outputs,
        "logs": cmd_logs,
        "stream": cmd_stream,
        "available": cmd_available,
        "shell": cmd_shell,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        print(f"{RED}Unknown command: {args.command}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
