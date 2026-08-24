"""CLI interface for the harness feature tracking system.

Usage:
    python -m harness <command> [options]

Commands:
    list        List features with optional filters
    show        Show feature details
    add         Add a new feature
    update      Update a feature field
    next        Show next feature to work on
    stats       Show statistics
    health      Validate database health
    sanitize    Normalize IDs and merge duplicates
    migrate     Import from feature_list.json
    export      Export to feature_list.json
    audit       Show audit trail for a feature
    session     Manage sessions
    search      Search features by text
"""

from __future__ import annotations

import argparse
import io
import sys

from harness.commands.admin import cmd_audit, cmd_export, cmd_health, cmd_migrate, cmd_sanitize, cmd_stats
from harness.commands.agents import build_agent_parser
from harness.commands.features import cmd_add, cmd_list, cmd_next, cmd_search, cmd_show, cmd_update
from harness.commands.sessions import cmd_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness",
        description="Feature tracking system for srt2web",
    )
    parser.add_argument("--db", default=None, help="Path to harness.db")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── list ──
    p = sub.add_parser("list", help="List features")
    p.add_argument("--status", choices=["pending", "in_progress", "done", "blocked"])
    p.add_argument("--area", help="Filter by area")
    p.add_argument("--priority", choices=["Alta", "Media", "Baja"])
    p.add_argument("--group", action="store_true", help="Group by status")
    p.set_defaults(func=cmd_list)

    # ── show ──
    p = sub.add_parser("show", help="Show feature details")
    p.add_argument("id", type=int, help="Feature ID")
    p.set_defaults(func=cmd_show)

    # ── add ──
    p = sub.add_parser("add", help="Add a new feature")
    p.add_argument("id", type=int, help="Feature ID")
    p.add_argument("name", help="Feature name (snake_case)")
    p.add_argument("title", help="Feature title")
    p.add_argument("--area", help="Area (core, frontend, security, etc.)")
    p.add_argument("--priority", choices=["Alta", "Media", "Baja"], default="Media")
    p.add_argument("--description", help="Description")
    p.add_argument("--agent", help="Agent name for audit")
    p.set_defaults(func=cmd_add)

    # ── update ──
    p = sub.add_parser("update", help="Update a feature field")
    p.add_argument("id", type=int, help="Feature ID")
    p.add_argument("field", help="Field name to update")
    p.add_argument("value", help="New value (JSON for lists/dicts)")
    p.add_argument("--agent", help="Agent name for audit")
    p.set_defaults(func=cmd_update)

    # ── next ──
    p = sub.add_parser("next", help="Show next feature to work on")
    p.set_defaults(func=cmd_next)

    # ── stats ──
    p = sub.add_parser("stats", help="Show statistics")
    p.set_defaults(func=cmd_stats)

    # ── health ──
    p = sub.add_parser("health", help="Validate database health")
    p.set_defaults(func=cmd_health)

    # ── sanitize ──
    p = sub.add_parser("sanitize", help="Normalize IDs and merge duplicates")
    p.set_defaults(func=cmd_sanitize)

    # ── migrate ──
    p = sub.add_parser("migrate", help="Import from feature_list.json")
    p.add_argument("file", nargs="?", default="feature_list.json", help="JSON file to import")
    p.set_defaults(func=cmd_migrate)

    # ── export ──
    p = sub.add_parser("export", help="Export to feature_list.json")
    p.add_argument("--output", help="Output file path")
    p.set_defaults(func=cmd_export)

    # ── audit ──
    p = sub.add_parser("audit", help="Show audit trail")
    p.add_argument("id", type=int, help="Feature ID")
    p.set_defaults(func=cmd_audit)

    # ── search ──
    p = sub.add_parser("search", help="Search features by text")
    p.add_argument("query", help="Search query")
    p.set_defaults(func=cmd_search)

    # ── session ──
    p = sub.add_parser("session", help="Manage sessions")
    sp = p.add_subparsers(dest="session_action")
    sp_start = sp.add_parser("start", help="Start a new session")
    sp_start.add_argument("--notes", help="Session notes")
    sp_list = sp.add_parser("list", help="List recent sessions")
    sp_list.add_argument("--limit", type=int, default=10)
    sp_end = sp.add_parser("end", help="End a session")
    sp_end.add_argument("session_id", type=int)
    sp_end.add_argument("--features", help="Comma-separated feature IDs worked on")
    sp_end.add_argument("--notes", help="Session notes")
    p.set_defaults(func=cmd_session)

    # ── agent ──
    build_agent_parser(sub)

    return parser


def main() -> None:
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
