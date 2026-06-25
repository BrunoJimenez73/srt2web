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
    migrate     Import from feature_list.json
    export      Export to feature_list.json
    audit       Show audit trail for a feature
    session     Manage sessions
    search      Search features by text
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .db import HarnessDB
from .models import Feature, RiskAssessment


def cmd_list(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    features = db.list_features(status=args.status, area=args.area, priority=args.priority)
    if not features:
        print("No features match the filters.")
        return

    if args.group:
        from collections import defaultdict

        groups: dict[str, list[Feature]] = defaultdict(list)
        for f in features:
            groups[f.status].append(f)
        for status in ["in_progress", "pending", "blocked", "done"]:
            if status not in groups:
                continue
            print(f"\n{'='*60}")
            print(f"  {status.upper()} ({len(groups[status])})")
            print(f"{'='*60}")
            for f in groups[status]:
                print(f"  F{f.numeric_id:>3} [{f.priority:>5}] {f.title}")
    else:
        for f in features:
            print(f"F{f.numeric_id:>3} [{f.status:>12}] [{f.priority:>5}] {f.title}")
    print(f"\nTotal: {len(features)} features")


def cmd_show(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    feature = db.get_feature(args.id)
    if not feature:
        print(f"Feature {args.id} not found.")
        sys.exit(1)

    print(f"Feature F{feature.numeric_id}")
    print(f"{'='*60}")
    print(f"  Name:       {feature.name}")
    print(f"  Title:      {feature.title}")
    print(f"  Status:     {feature.status}")
    print(f"  Area:       {feature.area}")
    print(f"  Priority:   {feature.priority}")
    if feature.phase:
        print(f"  Phase:      {feature.phase}")
    if feature.completed_date:
        print(f"  Completed:  {feature.completed_date}")
    if feature.started_in_session:
        print(f"  Started:    {feature.started_in_session}")
    if feature.dependencies:
        print(f"  Depends on: {', '.join(feature.dependencies)}")

    if feature.description:
        print(f"\n  Description:")
        print(f"    {feature.description}")

    if feature.problems_identified:
        print(f"\n  Problems identified:")
        for p in feature.problems_identified:
            print(f"    - {p}")

    if feature.acceptance:
        print(f"\n  Acceptance criteria:")
        for a in feature.acceptance:
            print(f"    - {a}")

    if feature.files_to_touch:
        print(f"\n  Files to touch:")
        for f in feature.files_to_touch:
            print(f"    - {f}")

    if feature.risk_assessment:
        print(f"\n  Risk: {feature.risk_assessment.risk_level}")
        for m in feature.risk_assessment.mitigation:
            print(f"    - {m}")

    if feature.fix:
        print(f"\n  Fix (what was done):")
        for f in feature.fix:
            print(f"    - {f}")

    if feature.completion_notes:
        print(f"\n  Notes: {feature.completion_notes}")


def cmd_add(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    if db.get_feature(args.id):
        print(f"Feature {args.id} already exists.")
        sys.exit(1)

    feature = Feature(
        id=args.id,
        name=args.name,
        title=args.title,
        status="pending",
        area=args.area or "",
        priority=args.priority or "Media",
        description=args.description or "",
    )
    db.upsert_feature(feature, agent=args.agent or "cli")
    print(f"Feature F{feature.numeric_id} created: {feature.title}")


def cmd_update(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    feature = db.get_feature(args.id)
    if not feature:
        print(f"Feature {args.id} not found.")
        sys.exit(1)

    value = args.value
    if args.field == "status":
        if value == "done" and not feature.completed_date:
            from datetime import datetime, timezone

            db.update_feature_field(
                args.id, "completed_date", datetime.now(timezone.utc).strftime("%Y-%m-%d"), agent=args.agent or "cli"
            )
        elif value == "in_progress" and not feature.started_in_session:
            from datetime import datetime, timezone

            db.update_feature_field(
                args.id,
                "started_in_session",
                datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                agent=args.agent or "cli",
            )

    if args.field in ("problems_identified", "acceptance", "files_to_touch", "fix", "dependencies"):
        try:
            parsed = json.loads(value)
            value = json.dumps(parsed)
        except json.JSONDecodeError:
            value = json.dumps([value])
    elif args.field == "risk_assessment":
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            print("risk_assessment must be valid JSON")
            sys.exit(1)
    elif args.field == "results":
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            print("results must be valid JSON")
            sys.exit(1)

    success = db.update_feature_field(args.id, args.field, value, agent=args.agent or "cli")
    if success:
        print(f"Feature F{args.id} field '{args.field}' updated.")
    else:
        print(f"Failed to update feature {args.id}.")


def cmd_next(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    feature = db.next_feature()
    if not feature:
        print("No pending features.")
        return
    print(f"Next: F{feature.numeric_id} [{feature.priority}] {feature.title}")
    if feature.description:
        print(f"  {feature.description[:120]}...")


def cmd_stats(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    counts = db.count_by_status()
    all_features = db.list_features()

    total = sum(counts.values())
    print(f"Feature Statistics")
    print(f"{'='*40}")
    for status in ["done", "in_progress", "pending", "blocked"]:
        cnt = counts.get(status, 0)
        pct = (cnt / total * 100) if total else 0
        bar = "#" * int(pct / 5) + "." * (20 - int(pct / 5))
        print(f"  {status:>12}: {cnt:>3} ({pct:5.1f}%) {bar}")
    print(f"  {'TOTAL':>12}: {total:>3}")

    from collections import Counter

    area_counts = Counter(f.area for f in all_features if f.area)
    if area_counts:
        print(f"\nBy Area:")
        for area, cnt in area_counts.most_common():
            print(f"  {area:>15}: {cnt}")


def cmd_health(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    result = db.health()
    if result["healthy"]:
        print("[OK] Database is healthy")
    else:
        print("[FAIL] Database has issues:")
        for issue in result["issues"]:
            print(f"  - {issue}")
    if result["stats"]:
        counts = result["stats"].get("counts_by_status", {})
        total = result["stats"].get("total_features", 0)
        print(f"  Features: {total} total")
        for s, c in counts.items():
            print(f"    {s}: {c}")
    sys.exit(0 if result["healthy"] else 1)


def cmd_migrate(args: argparse.Namespace) -> None:
    from .migrate import migrate

    result = migrate(args.file, args.db)
    print(f"Imported: {result['imported']} features")
    if result["skipped"]:
        print(f"Skipped: {result['skipped']}")
    for err in result["errors"]:
        print(f"  ERROR: {err}")


def cmd_export(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    data = db.export_to_dict()
    output = Path(args.output) if args.output else Path("feature_list_export.json")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Exported {len(data['features'])} features to {output}")


def cmd_audit(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    entries = db.get_audit_trail(args.id)
    if not entries:
        print(f"No audit entries for feature {args.id}.")
        return
    print(f"Audit trail for F{args.id}:")
    print(f"{'='*60}")
    for e in entries:
        print(f"  [{e.timestamp}] {e.field_name}: '{e.old_value}' -> '{e.new_value}' (by {e.agent})")


def cmd_search(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    all_features = db.list_features()
    query = args.query.lower()
    results = [
        f for f in all_features if query in f.name.lower() or query in f.title.lower() or query in f.description.lower()
    ]
    if not results:
        print(f"No features matching '{args.query}'.")
        return
    for f in results:
        print(f"F{f.numeric_id:>3} [{f.status:>12}] {f.title}")
    print(f"\nFound: {len(results)} features")


def cmd_session(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    if args.session_action == "start":
        session = db.start_session(args.notes or "")
        print(f"Session #{session.id} started on {session.date}")
    elif args.session_action == "list":
        sessions = db.list_sessions(limit=args.limit or 10)
        for s in sessions:
            print(f"  #{s.id} [{s.date}] {', '.join(s.features_worked) or '(none)'} -- {s.notes or '(no notes)'}")
    elif args.session_action == "end":
        features = args.features.split(",") if args.features else []
        db.end_session(args.session_id, features, args.notes or "")
        print(f"Session #{args.session_id} ended.")


def main() -> None:
    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="harness",
        description="Feature tracking system for srt2web",
    )
    parser.add_argument("--db", default=None, help="Path to harness.db")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    p = sub.add_parser("list", help="List features")
    p.add_argument("--status", choices=["pending", "in_progress", "done", "blocked"])
    p.add_argument("--area", help="Filter by area")
    p.add_argument("--priority", choices=["Alta", "Media", "Baja"])
    p.add_argument("--group", action="store_true", help="Group by status")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Show feature details")
    p.add_argument("id", type=int, help="Feature ID")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("add", help="Add a new feature")
    p.add_argument("id", type=int, help="Feature ID")
    p.add_argument("name", help="Feature name (snake_case)")
    p.add_argument("title", help="Feature title")
    p.add_argument("--area", help="Area (core, frontend, security, etc.)")
    p.add_argument("--priority", choices=["Alta", "Media", "Baja"], default="Media")
    p.add_argument("--description", help="Description")
    p.add_argument("--agent", help="Agent name for audit")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update", help="Update a feature field")
    p.add_argument("id", type=int, help="Feature ID")
    p.add_argument("field", help="Field name to update")
    p.add_argument("value", help="New value (JSON for lists/dicts)")
    p.add_argument("--agent", help="Agent name for audit")
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("next", help="Show next feature to work on")
    p.set_defaults(func=cmd_next)

    p = sub.add_parser("stats", help="Show statistics")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("health", help="Validate database health")
    p.set_defaults(func=cmd_health)

    p = sub.add_parser("migrate", help="Import from feature_list.json")
    p.add_argument("file", nargs="?", default="feature_list.json", help="JSON file to import")
    p.set_defaults(func=cmd_migrate)

    p = sub.add_parser("export", help="Export to feature_list.json")
    p.add_argument("--output", help="Output file path")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("audit", help="Show audit trail")
    p.add_argument("id", type=int, help="Feature ID")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("search", help="Search features by text")
    p.add_argument("query", help="Search query")
    p.set_defaults(func=cmd_search)

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

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
