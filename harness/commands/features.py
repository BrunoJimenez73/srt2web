"""Feature commands: list, show, add, update, next, search."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC

from harness.db import HarnessDB
from harness.models import Feature


def cmd_list(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    features = db.list_features(status=args.status, area=args.area, priority=args.priority)
    if not features:
        print("No features match the filters.")
        return

    if args.group:
        groups: dict[str, list[Feature]] = defaultdict(list)
        for f in features:
            groups[f.status].append(f)
        for status in ["in_progress", "pending", "blocked", "done"]:
            if status not in groups:
                continue
            print(f"\n{'=' * 60}")
            print(f"  {status.upper()} ({len(groups[status])})")
            print(f"{'=' * 60}")
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
    print(f"{'=' * 60}")
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
        print("\n  Description:")
        print(f"    {feature.description}")

    if feature.problems_identified:
        print("\n  Problems identified:")
        for p in feature.problems_identified:
            print(f"    - {p}")

    if feature.acceptance:
        print("\n  Acceptance criteria:")
        for a in feature.acceptance:
            print(f"    - {a}")

    if feature.files_to_touch:
        print("\n  Files to touch:")
        for f in feature.files_to_touch:
            print(f"    - {f}")

    if feature.risk_assessment:
        print(f"\n  Risk: {feature.risk_assessment.risk_level}")
        for m in feature.risk_assessment.mitigation:
            print(f"    - {m}")

    if feature.fix:
        print("\n  Fix (what was done):")
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
            from datetime import datetime

            db.update_feature_field(
                args.id, "completed_date", datetime.now(UTC).strftime("%Y-%m-%d"), agent=args.agent or "cli"
            )
        elif value == "in_progress" and not feature.started_in_session:
            from datetime import datetime

            db.update_feature_field(
                args.id,
                "started_in_session",
                datetime.now(UTC).strftime("%Y-%m-%d"),
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
