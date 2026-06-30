"""Session commands: start, list, end."""

from __future__ import annotations

import argparse

from harness.db import HarnessDB


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
