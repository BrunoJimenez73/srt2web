"""Admin commands: stats, health, sanitize, migrate, export, audit."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from harness.db import HarnessDB


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


def cmd_sanitize(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    result = db.sanitize_ids(agent="cli")
    print(f"Sanitize complete:")
    print(f"  Merged: {result['merged']} duplicate entries")
    print(f"  Errors: {len(result['errors'])}")
    for err in result["errors"]:
        print(f"    ERROR: {err}")
    if result["merged"]:
        print("Run 'python -m harness health' to verify.")


def cmd_migrate(args: argparse.Namespace) -> None:
    from harness.migrate import migrate

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
