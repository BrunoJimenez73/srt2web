"""Tests for the harness agent system (tester / builder / verifier)."""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from harness.cli import build_parser  # noqa: E402
from harness.db import HarnessDB  # noqa: E402
from harness.models import AgentFeedback, AgentTask, Feature  # noqa: E402


@pytest.fixture
def db() -> HarnessDB:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    d = HarnessDB(path)
    d.connect()
    yield d
    d.close()
    with contextlib.suppress(OSError):
        os.unlink(path)


@pytest.fixture
def feature(db: HarnessDB) -> Feature:
    f = Feature(id="200", name="agent_feature", title="Agent Feature", status="in_progress")
    db.upsert_feature(f, agent="test")
    return f


def fake_tests(all_passed: bool = False):
    def _fake(feature_id: str, skip_frontend: bool = False) -> dict:
        return {
            "all_passed": all_passed,
            "passed": 10,
            "failed": 0 if all_passed else 2,
            "tests_run": 10,
            "failures": [] if all_passed else ["FAILED tests/unit/test_x.py::test_a"],
        }

    return _fake


def fake_checks(approved: bool = True):
    def _fake(feature_id: str, skip_frontend: bool = False) -> dict:
        return {
            "approved": approved,
            "failures": [] if approved else ["FAILED tests/unit/test_y.py::test_b"],
            "pytest": {"all_passed": approved},
        }

    return _fake


class TestModels:
    def test_agent_is_active(self) -> None:
        from harness.models import Agent

        assert Agent(name="tester", role="tester", status="working").is_active
        assert not Agent(name="tester", role="tester", status="idle").is_active

    def test_feedback_needs_rework(self) -> None:
        assert AgentFeedback(task_id="t", approved=False).needs_rework
        assert not AgentFeedback(task_id="t", approved=True).needs_rework

    def test_task_can_retry(self) -> None:
        t = AgentTask(
            id="1",
            feature_id="1",
            agent_name="builder",
            type="implement",
            description="",
            status="feedback_received",
            iterations=2,
            max_iterations=5,
        )
        assert t.can_retry
        exhausted = AgentTask(
            id="1",
            feature_id="1",
            agent_name="builder",
            type="implement",
            description="",
            status="feedback_received",
            iterations=5,
            max_iterations=5,
        )
        assert not exhausted.can_retry

    def test_agent_task_no_broken_from_row(self) -> None:
        assert not hasattr(AgentFeedback, "from_row")


class TestAgentCRUD:
    def test_init_default_agents_idempotent(self, db: HarnessDB) -> None:
        db.init_default_agents()
        db.init_default_agents()
        names = [a.name for a in db.list_agents()]
        assert names == ["builder", "tester", "verifier"]

    def test_get_agent_missing(self, db: HarnessDB) -> None:
        assert db.get_agent("nope") is None

    def test_update_agent_status_with_task(self, db: HarnessDB) -> None:
        db.init_default_agents()
        db.update_agent_status("builder", "working", current_task_id="abc")
        agent = db.get_agent("builder")
        assert agent is not None and agent.status == "working" and agent.current_task_id == "abc"


class TestTaskLifecycle:
    def test_create_show_update_complete(self, db: HarnessDB, feature: Feature) -> None:
        task = db.create_agent_task("F200", "tester", "test", "desc", input_data={"a": 1})
        got = db.get_agent_task(task.id)
        assert got is not None and got.feature_id == "200" and got.input_data == {"a": 1}

        db.update_agent_task(task.id, status="in_progress", input_data={"b": 2}, iterations=1)
        got = db.get_agent_task(task.id)
        assert got is not None and got.status == "in_progress" and got.iterations == 1
        assert got is not None and got.input_data == {"b": 2}

        db.complete_agent_task(task.id, {"ok": True})
        got = db.get_agent_task(task.id)
        assert got is not None and got.status == "completed" and got.output_data == {"ok": True}
        assert got is not None and got.completed_at

    def test_list_filters(self, db: HarnessDB, feature: Feature) -> None:
        db.create_agent_task("F200", "tester", "test", "t1")
        db.create_agent_task("F200", "builder", "implement", "b1")
        assert len(db.list_agent_tasks(agent_name="builder")) == 1
        assert len(db.list_agent_tasks(status="pending")) == 2


class TestTesterPhase:
    def test_passing_round(self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch) -> None:
        db.init_default_agents()
        monkeypatch.setattr(db, "_run_tester_tests", fake_tests(all_passed=True))
        out = db.run_tester_phase("F200")
        assert out["all_passed"] and out["task_id"]
        task = db.get_agent_task(out["task_id"])
        assert task is not None and task.status == "completed"
        assert db.get_agent("tester") is not None
        assert db.get_agent("tester").status == "idle"

    def test_failing_round_reports_failures(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(db, "_run_tester_tests", fake_tests(all_passed=False))
        out = db.run_tester_phase("F200")
        assert not out["all_passed"]
        assert "test_x.py::test_a" in out["failures"][0]

    def test_unknown_feature(self, db: HarnessDB) -> None:
        out = db.run_tester_phase("9999")
        assert "error" in out


class TestBuilderTaskReuse:
    def test_creates_new_task(self, db: HarnessDB, feature: Feature) -> None:
        task = db.open_builder_task("F200", issues=["i1"], comments="c")
        assert task.status == "pending"
        assert task.iterations == 0
        assert task.input_data["issues"] == ["i1"]

    def test_reuses_retriable_task_and_accumulates_history(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        first = db.open_builder_task("F200", issues=["i1"])
        db.complete_agent_task(first.id, {})
        monkeypatch.setattr(db, "_run_verifier_checks", fake_checks(approved=False))
        res = db.run_verify_phase(first.id)
        assert not res["approved"] and res["iterations"] == 1

        reopened = db.open_builder_task("F200", issues=["i2"], comments="second round")
        assert reopened.id == first.id
        assert reopened.status == "pending"
        assert reopened.iterations == 1
        assert len(reopened.input_data["feedback_history"]) == 1

    def test_failed_task_not_reused(self, db: HarnessDB, feature: Feature) -> None:
        t = db.create_agent_task("F200", "builder", "implement", "d", max_iterations=3)
        db.update_agent_task(t.id, status="failed", iterations=3)
        fresh = db.open_builder_task("F200", issues=["x"])
        assert fresh.id != t.id
        assert fresh.iterations == 0


class TestVerifyPhase:
    def test_errors(self, db: HarnessDB, feature: Feature) -> None:
        assert "error" in db.run_verify_phase("nonexistent")

        t = db.create_agent_task("F200", "tester", "test", "not a build task")
        assert "error" in db.run_verify_phase(t.id)

        b = db.create_agent_task("F200", "builder", "implement", "pending build")
        assert "error" in db.run_verify_phase(b.id)

    def test_approved_records_feedback_against_build_task(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        build = db.open_builder_task("F200")
        db.complete_agent_task(build.id, {"done": True})
        monkeypatch.setattr(db, "_run_verifier_checks", fake_checks(approved=True))

        res = db.run_verify_phase(build.id)
        assert res["approved"]
        fb = db.get_latest_feedback(build.id)
        assert fb is not None and fb.approved
        # feedback must target the BUILD task, not the verify task
        verify_task = db.get_agent_task(res["task_id"])
        assert verify_task is not None and verify_task.agent_name == "verifier"

    def test_rejection_reopens_with_feedback(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        build = db.open_builder_task("F200")
        db.complete_agent_task(build.id, {})
        monkeypatch.setattr(db, "_run_verifier_checks", fake_checks(approved=False))

        res = db.run_verify_phase(build.id)
        assert not res["approved"] and res["iterations"] == 1 and not res["exhausted"]

        task = db.get_agent_task(build.id)
        assert task is not None and task.status == "feedback_received" and task.iterations == 1
        fb = db.get_latest_feedback(build.id)
        assert fb is not None and fb.needs_rework and fb.issues

    def test_exhaustion_fails_task(self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch) -> None:
        build = db.open_builder_task("F200")
        db.update_agent_task(build.id, iterations=4)  # one left before max_iterations=5
        db.complete_agent_task(build.id, {})
        monkeypatch.setattr(db, "_run_verifier_checks", fake_checks(approved=False))

        res = db.run_verify_phase(build.id)
        assert res["exhausted"] and res["iterations"] == 5
        task = db.get_agent_task(build.id)
        assert task is not None and task.status == "failed"


class TestFullCycle:
    def test_all_passed_first_round(self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(db, "_run_tester_tests", fake_tests(all_passed=True))
        res = db.run_agent_cycle("F200")
        assert res["final_status"] == "all_tests_passed"

    def test_awaits_external_builder_without_hook(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(db, "_run_tester_tests", fake_tests(all_passed=False))
        res = db.run_agent_cycle("F200")
        assert res["final_status"] == "awaiting_builder"
        assert res["build_task_id"]
        task = db.get_agent_task(res["build_task_id"])
        assert task is not None and task.status == "pending"
        assert "test_a" in task.input_data["issues"][0]

    def test_loop_until_approval_with_hook(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(db, "_run_tester_tests", fake_tests(all_passed=False))
        checks = {"approved": False}

        def verifier(feature_id: str, skip_frontend: bool = False) -> dict:
            return {"approved": checks["approved"], "failures": [] if checks["approved"] else ["still broken"]}

        monkeypatch.setattr(db, "_run_verifier_checks", verifier)

        import harness.runner as runner_mod

        hook_calls = {"n": 0}

        def fake_hook(cmd: str, cwd=None, timeout_s: int = 3600, env: dict | None = None) -> dict:
            task_id = (env or {}).get("HARNESS_TASK_ID", "")
            if task_id:
                hook_calls["n"] += 1
                if hook_calls["n"] >= 2:
                    checks["approved"] = True  # builder "fixes" the issue on 2nd pass
                db.complete_agent_task(task_id, {"pass": hook_calls["n"]})
            return {"cmd": cmd, "exit_code": 0, "stdout_tail": "", "stderr_tail": "", "timed_out": False}

        monkeypatch.setattr(runner_mod, "run_shell_command", fake_hook)

        res = db.run_agent_cycle("F200", max_cycles=3, builder_hook="noop")
        assert res["final_status"] == "approved"
        assert len(res["cycles"]) == 2
        assert hook_calls["n"] == 2

    def test_hook_that_does_not_complete_task(
        self, db: HarnessDB, feature: Feature, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(db, "_run_tester_tests", fake_tests(all_passed=False))

        import harness.runner as runner_mod

        monkeypatch.setattr(
            runner_mod,
            "run_shell_command",
            lambda cmd, cwd=None, timeout_s=3600, env=None: {
                "cmd": cmd,
                "exit_code": 0,
                "stdout_tail": "",
                "stderr_tail": "",
                "timed_out": False,
            },
        )

        res = db.run_agent_cycle("F200", max_cycles=3, builder_hook="noop")
        assert res["final_status"] == "awaiting_builder_manual"


class TestRunnerParsers:
    def test_parse_pytest_summary(self) -> None:
        from harness.runner import parse_pytest_summary

        counts = parse_pytest_summary("1594 passed, 12 skipped in 120.00s")
        assert counts == {"passed": 1594, "failed": 0, "skipped": 12, "errors": 0, "warnings": 0}
        counts2 = parse_pytest_summary("2 failed, 40 passed, 1 warning in 5.00s")
        assert counts2["failed"] == 2 and counts2["warnings"] == 1

    def test_parse_pytest_failures(self) -> None:
        from harness.runner import parse_pytest_failures

        out = (
            "FAILED tests/unit/test_x.py::test_a - assert False\n"
            "ERROR tests/unit/test_y.py::test_b - PermissionError: [WinError 5]\n"
            "FAILED tests/unit/test_z.py::test_c\n"
            "2 failed, 1 error"
        )
        lines = parse_pytest_failures(out)
        assert len(lines) == 3
        assert lines[0].startswith("FAILED ")
        assert lines[1].startswith("ERROR ")

    def test_run_pytest_requests_failed_and_error_summary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import harness.runner as runner_mod

        captured: dict = {}

        def fake_run_command(cmd, cwd=None, timeout_s=3600):
            captured["cmd"] = cmd
            return {
                "cmd": cmd,
                "exit_code": 0,
                "stdout_tail": "10 passed in 1.00s",
                "stderr_tail": "",
                "timed_out": False,
            }

        monkeypatch.setattr(runner_mod, "run_command", fake_run_command)
        res = runner_mod.run_pytest(PROJECT_ROOT)
        assert "-rfE" in captured["cmd"]
        assert res["all_passed"] and res["passed"] == 10

    def test_run_command_file_not_found(self) -> None:
        from harness.runner import run_command

        res = run_command(["definitely-missing-binary-xyz"])
        assert res["exit_code"] is None and "not found" in res["stderr_tail"]


class TestCLIParser:
    def test_agent_test_args(self) -> None:
        args = build_parser().parse_args(["agent", "test", "--feature", "F123"])
        assert args.feature == "F123" and not args.skip_frontend

    def test_agent_verify_args(self) -> None:
        args = build_parser().parse_args(["agent", "verify", "--task-id", "abc", "--skip-frontend"])
        assert args.task_id == "abc" and args.skip_frontend

    def test_agent_cycle_hook(self) -> None:
        args = build_parser().parse_args(["agent", "cycle", "--feature", "1", "--hook", "echo hi", "--max-cycles", "2"])
        assert args.hook == "echo hi" and args.max_cycles == 2

    def test_agent_task_update_input(self) -> None:
        args = build_parser().parse_args(["agent", "task", "update", "--task-id", "x", "--input", '{"a":1}'])
        assert args.input == '{"a":1}'
