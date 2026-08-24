"""Real command execution for agent phases (tester / verifier).

Runs pytest and the frontend vitest suite, parses summaries and returns
structured results that the harness stores as task output_data.
"""

from __future__ import annotations

import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_TIMEOUT_S = 3600
OUTPUT_TAIL_LINES = 80

_PYTEST_SUMMARY_PATTERNS = [
    ("failed", re.compile(r"(\d+)\s+failed")),
    ("errors", re.compile(r"(\d+)\s+error")),
    ("passed", re.compile(r"(\d+)\s+passed")),
    ("skipped", re.compile(r"(\d+)\s+skipped")),
    ("warnings", re.compile(r"(\d+)\s+warning")),
]


def _tail(text: str, max_lines: int = OUTPUT_TAIL_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[-max_lines:])


def run_command(
    cmd: list[str],
    cwd: Path | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any]:
    """Run a command capturing output. Never raises on non-zero exit."""
    start = time.monotonic()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=False,
            timeout=timeout_s,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
        return {
            "cmd": cmd,
            "exit_code": proc.returncode,
            "duration_s": round(time.monotonic() - start, 1),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "cmd": cmd,
            "exit_code": None,
            "duration_s": round(time.monotonic() - start, 1),
            "stdout_tail": "",
            "stderr_tail": f"Timed out after {timeout_s}s",
            "timed_out": True,
        }
    except FileNotFoundError:
        return {
            "cmd": cmd,
            "exit_code": None,
            "duration_s": round(time.monotonic() - start, 1),
            "stdout_tail": "",
            "stderr_tail": f"Command not found: {cmd[0]}",
            "timed_out": False,
        }


def run_shell_command(
    cmd: str,
    cwd: Path | None = None,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a shell command string (user-configured hooks). Never raises."""
    import os

    start = time.monotonic()
    full_env = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=False,
            timeout=timeout_s,
            shell=True,
            env=full_env,
        )
        stdout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
        stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
        return {
            "cmd": cmd,
            "exit_code": proc.returncode,
            "duration_s": round(time.monotonic() - start, 1),
            "stdout_tail": _tail(stdout),
            "stderr_tail": _tail(stderr),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "cmd": cmd,
            "exit_code": None,
            "duration_s": round(time.monotonic() - start, 1),
            "stdout_tail": "",
            "stderr_tail": f"Timed out after {timeout_s}s",
            "timed_out": True,
        }


def parse_pytest_summary(output: str) -> dict[str, int]:
    """Extract pass/fail/skip/error counts from a pytest summary line."""
    counts = {"passed": 0, "failed": 0, "skipped": 0, "errors": 0, "warnings": 0}
    for line in output.splitlines():
        for key, pattern in _PYTEST_SUMMARY_PATTERNS:
            m = pattern.search(line)
            if m:
                counts[key] = int(m.group(1))
    return counts


def parse_pytest_failures(output: str) -> list[str]:
    """Extract 'FAILED test::name' / 'ERROR test::name' lines emitted by pytest -rfE."""
    return [line.strip() for line in output.splitlines() if line.strip().startswith(("FAILED ", "ERROR "))]


def run_pytest(
    project_root: Path,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Run the unit test suite with pytest and parse the result."""
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/unit/",
        "-q",
        "--tb=no",
        "-rfE",
        "-p",
        "no:cacheprovider",
        *(extra_args or []),
    ]
    res = run_command(cmd, cwd=project_root, timeout_s=timeout_s)
    combined = "\n".join([res["stdout_tail"], res["stderr_tail"]])
    counts = parse_pytest_summary(combined)
    failures = parse_pytest_failures(combined)
    ok = res["exit_code"] == 0 and not res["timed_out"]
    return {
        **res,
        "ok": ok,
        "all_passed": ok,
        "passed": counts["passed"],
        "failed": counts["failed"],
        "skipped": counts["skipped"],
        "errors": counts["errors"],
        "failures": failures,
        "tests_run": counts["passed"] + counts["failed"] + counts["skipped"],
    }


def run_frontend_tests(
    project_root: Path,
    frontend_dir: str = "frontend",
    timeout_s: int = DEFAULT_TIMEOUT_S,
) -> dict[str, Any] | None:
    """Run the frontend vitest suite. Returns None if dependencies are missing.

    Uses ``npx vitest run`` because package.json's ``test`` script defaults
    to watch mode.
    """
    fe = project_root / frontend_dir
    if not (fe / "node_modules").is_dir():
        return None
    npx = "npx.cmd" if sys.platform == "win32" else "npx"
    res = run_command([npx, "vitest", "run"], cwd=fe, timeout_s=timeout_s)
    combined = "\n".join([res["stdout_tail"], res["stderr_tail"]])
    passed_m = re.search(r"(\d+)\s+passed", combined)
    failed_m = re.search(r"(\d+)\s+failed", combined)
    ok = res["exit_code"] == 0 and not res["timed_out"]
    return {
        **res,
        "ok": ok,
        "all_passed": ok,
        "passed": int(passed_m.group(1)) if passed_m else 0,
        "failed": int(failed_m.group(1)) if failed_m else 0,
        "failures": [] if ok else ["Frontend tests failed (see stdout_tail)"],
    }
