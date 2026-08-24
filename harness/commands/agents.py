"""Agent commands: list, init, status, test, task, verify, cycle, feedback."""

from __future__ import annotations

import argparse
import json
import sys

from harness.db import HarnessDB


def cmd_agent_list(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    agents = db.list_agents()
    if not agents:
        print("No agents found. Run 'harness agent init' to create defaults.")
        return

    print(f"{'NAME':<12} {'ROLE':<10} {'STATUS':<15} {'CURRENT_TASK'}")
    print("-" * 60)
    for a in agents:
        task = a.current_task_id or "-"
        print(f"{a.name:<12} {a.role:<10} {a.status:<15} {task}")


def cmd_agent_init(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    db.init_default_agents()
    print("Initialized default agents: tester, builder, verifier")
    cmd_agent_list(args)


def cmd_agent_status(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    if args.name:
        agent = db.get_agent(args.name)
        if not agent:
            print(f"Agent '{args.name}' not found.")
            sys.exit(1)
        agents = [agent]
    else:
        agents = db.list_agents()

    for a in agents:
        print(f"Agent: {a.name} ({a.role})")
        print(f"  Status:       {a.status}")
        print(f"  Description:  {a.description}")
        print(f"  Config:       {json.dumps(a.config, ensure_ascii=False)}")
        print(f"  Current Task: {a.current_task_id or 'none'}")
        print(f"  Created:      {a.created_at}")
        print(f"  Updated:      {a.updated_at}")
        print()


def cmd_agent_task(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)

    if args.action == "create":
        if not args.feature or not args.agent or not args.type or not args.description:
            print("Usage: harness agent task create --feature F123 --agent tester --type test --description '...'")
            sys.exit(1)

        task = db.create_agent_task(
            feature_id=args.feature,
            agent_name=args.agent,
            task_type=args.type,
            description=args.description,
            input_data=json.loads(args.input) if args.input else None,
            max_iterations=args.max_iterations,
        )
        print(f"Created task {task.id} for {args.agent} on feature {args.feature}")

    elif args.action == "list":
        tasks = db.list_agent_tasks(
            feature_id=args.feature,
            agent_name=args.agent,
            status=args.status,
        )
        if not tasks:
            print("No tasks found.")
            return

        print(f"{'ID':<10} {'FEATURE':<8} {'AGENT':<10} {'TYPE':<10} {'STATUS':<18} {'DESCRIPTION'}")
        print("-" * 100)
        for t in tasks:
            desc = t.description[:60] + "..." if len(t.description) > 60 else t.description
            print(f"{t.id:<10} {t.feature_id:<8} {t.agent_name:<10} {t.type:<10} {t.status:<18} {desc}")

    elif args.action == "show":
        if not args.task_id:
            print("Usage: harness agent task show --task-id XXX")
            sys.exit(1)
        task = db.get_agent_task(args.task_id)
        if not task:
            print(f"Task {args.task_id} not found.")
            sys.exit(1)

        print(f"Task: {task.id}")
        print(f"  Feature:      {task.feature_id}")
        print(f"  Agent:        {task.agent_name}")
        print(f"  Type:         {task.type}")
        print(f"  Status:       {task.status}")
        print(f"  Iterations:   {task.iterations}/{task.max_iterations}")
        print(f"  Description:  {task.description}")
        print(f"  Input:        {json.dumps(task.input_data, ensure_ascii=False, indent=2)}")
        print(f"  Output:       {json.dumps(task.output_data, ensure_ascii=False, indent=2)}")
        print(f"  Created:      {task.created_at}")
        print(f"  Updated:      {task.updated_at}")
        print(f"  Completed:    {task.completed_at or 'pending'}")

    elif args.action == "complete":
        if not args.task_id:
            print("Usage: harness agent task complete --task-id XXX [--output '{}']")
            sys.exit(1)
        output = json.loads(args.output) if args.output else None
        db.complete_agent_task(args.task_id, output)
        print(f"Task {args.task_id} marked as completed.")

    elif args.action == "update":
        if not args.task_id:
            print(
                "Usage: harness agent task update --task-id XXX [--status STATUS] [--output '{}'] [--input '{}'] [--iterations N]"
            )
            sys.exit(1)
        output = json.loads(args.output) if args.output else None
        input_data = json.loads(args.input) if getattr(args, "input", None) else None
        iterations = args.iterations if args.iterations is not None else None
        db.update_agent_task(
            args.task_id, status=args.status, output_data=output, iterations=iterations, input_data=input_data
        )
        print(f"Task {args.task_id} updated.")

    else:
        print(f"Unknown task action: {args.action}")
        sys.exit(1)


def _print_phase_result(out: dict, kind: str) -> None:
    """Print a tester/verifier phase result."""
    if "error" in out:
        print(f"ERROR: {out['error']}")
        return
    if kind == "test":
        print(f"Test task:   {out.get('task_id', 'N/A')}")
        errors = out.get("errors", 0)
        counts = f"passed={out.get('passed', '?')}  failed={out.get('failed', '?')}"
        if errors:
            counts += f"  ERRORS={errors}"
        print(f"Tests run:   {out.get('tests_run', '?')}  {counts}")
        fe = out.get("frontend")
        if isinstance(fe, dict):
            if fe.get("skipped"):
                print(f"Frontend:    skipped ({fe.get('reason', 'n/a')})")
            else:
                print(f"Frontend:    passed={fe.get('passed', '?')} failed={fe.get('failed', '?')}")
        print(f"All passed:  {out.get('all_passed')}")
        for f in out.get("failures", [])[:20]:
            print(f"  - {f}")
        if len(out.get("failures", [])) > 20:
            print(f"  ... and {len(out['failures']) - 20} more")
    elif kind == "verify":
        print(f"Verify task: {out.get('task_id', 'N/A')}")
        print(f"Build task:  {out.get('build_task_id', 'N/A')}")
        print(f"Approved:    {out.get('approved')}")
        for i in out.get("issues", []):
            print(f"  Issue: {i}")
        for s in out.get("suggestions", []):
            print(f"  Suggestion: {s}")
        if not out.get("approved") and not out.get("exhausted"):
            print("Builder task reopened with feedback (status: feedback_received).")


def cmd_agent_test(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    if not args.feature:
        print("Usage: harness agent test --feature F123 [--skip-frontend]")
        sys.exit(1)
    feature = db.get_feature(args.feature)
    title = feature.title if feature else ""
    print(f"TESTER: running real test suite (feature {args.feature}: {title})...")
    out = db.run_tester_phase(args.feature, skip_frontend=args.skip_frontend)
    _print_phase_result(out, "test")
    if not out.get("all_passed"):
        sys.exit(1)


def cmd_agent_verify(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)
    if not args.task_id:
        print("Usage: harness agent verify --task-id XXX [--skip-frontend]")
        sys.exit(1)
    print(f"VERIFIER: checking build task {args.task_id} with real checks...")
    out = db.run_verify_phase(args.task_id, skip_frontend=args.skip_frontend)
    _print_phase_result(out, "verify")
    if not out.get("approved"):
        sys.exit(1)


def cmd_agent_cycle(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)

    if not args.feature:
        print("Usage: harness agent cycle --feature F123 [--max-cycles 5] [--hook 'cmd'] [--skip-frontend]")
        sys.exit(1)

    mode = f"hook: {args.hook}" if args.hook else "manual builder"
    print(f"Running agent cycle for feature {args.feature} ({mode})...")
    result = db.run_agent_cycle(
        args.feature,
        max_cycles=args.max_cycles,
        builder_hook=args.hook,
        skip_frontend=args.skip_frontend,
    )

    print("\n" + "=" * 60)
    print(f"CYCLE RESULT FOR FEATURE {args.feature}")
    print("=" * 60)
    print(f"Final status: {result['final_status']}")

    if result["final_status"] == "awaiting_builder":
        print(f"\nBuilder task {result['build_task_id']} is pending.")
        print("An external builder session must now:")
        print("  1. Implement fixes for the issues reported by tester")
        print(f"     (see: python -m harness agent task show --task-id {result['build_task_id']})")
        print(
            f"  2. Mark done: python -m harness agent task complete --task-id {result['build_task_id']} --output '{{...}}'"
        )
        print(f"  3. Verify:    python -m harness agent verify --task-id {result['build_task_id']}")
        print("Verification rejection reopens the task automatically until approved.")

    for cycle in result.get("cycles", []):
        print(f"\n  Cycle {cycle['cycle']}:")
        test_res = cycle.get("test_result", {})
        print(f"    Test result: passed={test_res.get('passed', 0)}, failed={test_res.get('failed', 0)}")
        for f in test_res.get("failures", [])[:10]:
            print(f"      - {f}")

        verify_out = cycle.get("verify_result", {})
        if verify_out:
            print(f"    Approved:    {verify_out.get('approved', False)}")

    print("\n" + "=" * 60)
    if result["final_status"] not in ("approved", "all_tests_passed"):
        sys.exit(1)


def cmd_agent_feedback(args: argparse.Namespace) -> None:
    db = HarnessDB(args.db)

    if args.action == "give":
        if not args.task_id:
            print(
                "Usage: harness agent feedback give --task-id XXX --approved true/false [--comments '...'] [--issues '[]'] [--suggestions '[]']"
            )
            sys.exit(1)

        approved = args.approved.lower() == "true"
        issues = json.loads(args.issues) if args.issues else []
        suggestions = json.loads(args.suggestions) if args.suggestions else []

        feedback = db.save_agent_feedback(
            task_id=args.task_id,
            approved=approved,
            comments=args.comments or "",
            issues=issues,
            suggestions=suggestions,
        )
        print(f"Feedback saved for task {args.task_id}: {'APPROVED' if approved else 'NEEDS REWORK'}")
        if issues:
            print("Issues:")
            for i in issues:
                print(f"  - {i}")
        if suggestions:
            print("Suggestions:")
            for s in suggestions:
                print(f"  - {s}")

    elif args.action == "show":
        if not args.task_id:
            print("Usage: harness agent feedback show --task-id XXX")
            sys.exit(1)
        feedbacks = db.get_feedback_for_task(args.task_id)
        if not feedbacks:
            print(f"No feedback for task {args.task_id}.")
            return

        for fb in feedbacks:
            print(f"Feedback for task {fb.task_id} at {fb.created_at}:")
            print(f"  Approved:   {fb.approved}")
            print(f"  Comments:   {fb.comments or 'none'}")
            if fb.issues:
                print("  Issues:")
                for i in fb.issues:
                    print(f"    - {i}")
            if fb.suggestions:
                print("  Suggestions:")
                for s in fb.suggestions:
                    print(f"    - {s}")

    elif args.action == "latest":
        if not args.task_id:
            print("Usage: harness agent feedback latest --task-id XXX")
            sys.exit(1)
        fb = db.get_latest_feedback(args.task_id)
        if not fb:
            print(f"No feedback for task {args.task_id}.")
            return

        print(f"Latest feedback for task {fb.task_id}:")
        print(f"  Approved: {fb.approved}")
        print(f"  Needs rework: {fb.needs_rework}")

    else:
        print(f"Unknown feedback action: {args.action}")
        sys.exit(1)


def build_agent_parser(subparsers) -> None:
    p = subparsers.add_parser("agent", help="Manage agents (tester, builder, verifier)")
    sp = p.add_subparsers(dest="agent_action", help="Agent actions")

    # agent list
    sp_list = sp.add_parser("list", help="List agents")
    sp_list.set_defaults(func=cmd_agent_list)

    # agent init
    sp_init = sp.add_parser("init", help="Initialize default agents")
    sp_init.set_defaults(func=cmd_agent_init)

    # agent status
    sp_status = sp.add_parser("status", help="Show agent status")
    sp_status.add_argument("name", nargs="?", help="Agent name (tester, builder, verifier)")
    sp_status.set_defaults(func=cmd_agent_status)

    # agent task
    sp_task = sp.add_parser("task", help="Manage agent tasks")
    sp_task_sub = sp_task.add_subparsers(dest="action", help="Task actions")

    sp_tc = sp_task_sub.add_parser("create", help="Create a task")
    sp_tc.add_argument("--feature", required=True, help="Feature ID")
    sp_tc.add_argument("--agent", required=True, choices=["tester", "builder", "verifier"], help="Agent name")
    sp_tc.add_argument("--type", required=True, choices=["test", "implement", "verify"], help="Task type")
    sp_tc.add_argument("--description", required=True, help="Task description")
    sp_tc.add_argument("--input", help="Input data as JSON")
    sp_tc.add_argument("--max-iterations", type=int, default=5, help="Max iterations for builder")
    sp_tc.set_defaults(func=cmd_agent_task)

    sp_tl = sp_task_sub.add_parser("list", help="List tasks")
    sp_tl.add_argument("--feature", help="Filter by feature ID")
    sp_tl.add_argument("--agent", choices=["tester", "builder", "verifier"], help="Filter by agent")
    sp_tl.add_argument(
        "--status",
        choices=["pending", "in_progress", "completed", "failed", "feedback_received"],
        help="Filter by status",
    )
    sp_tl.set_defaults(func=cmd_agent_task)

    sp_ts = sp_task_sub.add_parser("show", help="Show task details")
    sp_ts.add_argument("--task-id", required=True, help="Task ID")
    sp_ts.set_defaults(func=cmd_agent_task)

    sp_tcp = sp_task_sub.add_parser("complete", help="Complete a task")
    sp_tcp.add_argument("--task-id", required=True, help="Task ID")
    sp_tcp.add_argument("--output", help="Output data as JSON")
    sp_tcp.set_defaults(func=cmd_agent_task)

    sp_tu = sp_task_sub.add_parser("update", help="Update a task")
    sp_tu.add_argument("--task-id", required=True, help="Task ID")
    sp_tu.add_argument(
        "--status", choices=["pending", "in_progress", "completed", "failed", "feedback_received"], help="New status"
    )
    sp_tu.add_argument("--output", help="Output data as JSON")
    sp_tu.add_argument("--input", help="Input data as JSON")
    sp_tu.add_argument("--iterations", type=int, help="Iteration count")
    sp_tu.set_defaults(func=cmd_agent_task)

    # agent test
    sp_test = sp.add_parser("test", help="Run tester phase (real tests) for a feature")
    sp_test.add_argument("--feature", required=True, help="Feature ID")
    sp_test.add_argument("--skip-frontend", action="store_true", help="Skip frontend vitest suite")
    sp_test.set_defaults(func=cmd_agent_test)

    # agent verify
    sp_verify = sp.add_parser("verify", help="Verify a completed builder task (real checks)")
    sp_verify.add_argument("--task-id", required=True, help="Builder task ID to verify")
    sp_verify.add_argument("--skip-frontend", action="store_true", help="Skip frontend vitest suite")
    sp_verify.set_defaults(func=cmd_agent_verify)

    # agent cycle
    sp_cycle = sp.add_parser("cycle", help="Run tester→builder→verifier cycle")
    sp_cycle.add_argument("--feature", required=True, help="Feature ID")
    sp_cycle.add_argument("--max-cycles", type=int, default=5, help="Maximum cycles to run")
    sp_cycle.add_argument("--hook", help="Shell command executed as the builder between tester and verifier")
    sp_cycle.add_argument("--skip-frontend", action="store_true", help="Skip frontend vitest suite")
    sp_cycle.set_defaults(func=cmd_agent_cycle)

    # agent feedback
    sp_feedback = sp.add_parser("feedback", help="Manage verifier feedback")
    sp_feedback_sub = sp_feedback.add_subparsers(dest="action", help="Feedback actions")

    sp_fb_give = sp_feedback_sub.add_parser("give", help="Give feedback (verifier → builder)")
    sp_fb_give.add_argument("--task-id", required=True, help="Task ID to give feedback on")
    sp_fb_give.add_argument("--approved", required=True, choices=["true", "false"], help="Whether approved")
    sp_fb_give.add_argument("--comments", help="Comments")
    sp_fb_give.add_argument("--issues", help="Issues as JSON array")
    sp_fb_give.add_argument("--suggestions", help="Suggestions as JSON array")
    sp_fb_give.set_defaults(func=cmd_agent_feedback)

    sp_fb_show = sp_feedback_sub.add_parser("show", help="Show all feedback for a task")
    sp_fb_show.add_argument("--task-id", required=True, help="Task ID")
    sp_fb_show.set_defaults(func=cmd_agent_feedback)

    sp_fb_latest = sp_feedback_sub.add_parser("latest", help="Show latest feedback for a task")
    sp_fb_latest.add_argument("--task-id", required=True, help="Task ID")
    sp_fb_latest.set_defaults(func=cmd_agent_feedback)
