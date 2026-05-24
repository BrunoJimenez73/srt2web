"""
Workflow Validator - Ejecuta todos los checks de calidad y produce un report.

Uso:
    python -m workflow.validator                        # all checks
    python -m workflow.validator --category python      # solo Python checks
    python -m workflow.validator --category frontend     # solo frontend checks
    python -m workflow.validator --json                  # output como JSON
"""

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("workflow.validator")

ROOT = Path(__file__).parent.parent


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration_ms: float
    output: str = ""
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def status_emoji(self) -> str:
        return "[OK]" if self.passed else "[FAIL]"

    @property
    def summary(self) -> str:
        return f"{self.status_emoji} {self.name}: {'PASSED' if self.passed else 'FAILED'} ({self.duration_ms:.0f}ms)"


class WorkflowValidator:
    """Ejecuta checks de calidad y produce un reporte estructurado."""

    def __init__(self, python_path: str = "") -> None:
        self._python = python_path or self._detect_python()
        self._results: list[CheckResult] = []

    def _detect_python(self) -> str:
        candidates = [
            str(ROOT / "venv" / "Scripts" / "python.exe"),
            str(ROOT / "venv" / "bin" / "python"),
            "python",
            "python3",
        ]
        for c in candidates:
            try:
                subprocess.run([c, "--version"], capture_output=True, timeout=5)
                return c
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "python"

    def _run(self, cmd: list[str], timeout: int = 120, cwd: Optional[Path] = None) -> tuple[int, str, str]:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd or ROOT)
            return r.returncode, r.stdout, r.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "TIMEOUT"
        except FileNotFoundError as e:
            return -1, "", f"Not found: {e}"

    # ── Python Checks ──────────────────────────────────────────────────

    def check_pytest(self) -> CheckResult:
        start = time.perf_counter()
        rc, out, err = self._run(
            [self._python, "-m", "pytest", "tests/unit/", "-q", "--tb=short", "-m", "not slow"], timeout=180
        )
        passed = rc == 0
        return CheckResult(
            name="pytest",
            passed=passed,
            duration_ms=(time.perf_counter() - start) * 1000,
            output=out.strip(),
            error=err.strip(),
        )

    def check_mypy(self) -> CheckResult:
        start = time.perf_counter()
        rc, out, err = self._run([self._python, "-m", "mypy", "core/", "server/", "--strict"], timeout=120)
        passed = rc == 0
        return CheckResult(
            name="mypy",
            passed=passed,
            duration_ms=(time.perf_counter() - start) * 1000,
            output=out.strip(),
            error=err.strip(),
        )

    def check_ruff(self) -> CheckResult:
        start = time.perf_counter()
        rc, out, err = self._run(
            [self._python, "-m", "ruff", "check", "core/", "modules/", "server/", "tests/"], timeout=60
        )
        passed = rc == 0
        return CheckResult(
            name="ruff",
            passed=passed,
            duration_ms=(time.perf_counter() - start) * 1000,
            output=out.strip(),
            error=err.strip(),
        )

    # ── Frontend Checks ────────────────────────────────────────────────

    def check_tsc(self) -> CheckResult:
        start = time.perf_counter()
        tsc = ROOT / "frontend" / "node_modules" / ".bin" / "tsc"
        if not tsc.exists():
            return CheckResult(name="tsc", passed=True, duration_ms=0, details={"skipped": "tsc not available"})
        rc, out, err = self._run([str(tsc), "--noEmit"], timeout=60, cwd=ROOT / "frontend")
        passed = rc == 0
        return CheckResult(
            name="tsc",
            passed=passed,
            duration_ms=(time.perf_counter() - start) * 1000,
            output=out.strip(),
            error=err.strip(),
        )

    # ── Repository Checks ──────────────────────────────────────────────

    def check_feature_list(self) -> CheckResult:
        start = time.perf_counter()
        fl = ROOT / "feature_list.json"
        if not fl.exists():
            return CheckResult(name="feature_list", passed=False, duration_ms=0, error="feature_list.json not found")
        try:
            import json

            data = json.loads(fl.read_text(encoding="utf-8"))
            features = data.get("features", [])
            in_progress = [f for f in features if f.get("status") == "in_progress"]
            valid_statuses = {"pending", "in_progress", "done", "blocked"}
            invalid = [f for f in features if f.get("status") not in valid_statuses]
            errors = []
            if len(in_progress) > 1:
                errors.append(f"{len(in_progress)} features en in_progress (max 1)")
            if invalid:
                errors.append(f"{len(invalid)} features con status inválido")
            return CheckResult(
                name="feature_list",
                passed=len(errors) == 0,
                duration_ms=(time.perf_counter() - start) * 1000,
                details={"features": len(features), "in_progress": len(in_progress), "errors": errors},
                error="; ".join(errors),
            )
        except Exception as e:
            return CheckResult(
                name="feature_list", passed=False, duration_ms=(time.perf_counter() - start) * 1000, error=str(e)
            )

    def check_checkpoints(self) -> CheckResult:
        start = time.perf_counter()
        required = ["AGENTS.md", "CHECKPOINTS.md", "feature_list.json", "progress/current.md", "progress/history.md"]
        missing = [f for f in required if not (ROOT / f).exists()]
        return CheckResult(
            name="checkpoints",
            passed=len(missing) == 0,
            duration_ms=(time.perf_counter() - start) * 1000,
            details={"missing": missing},
            error=f"Missing: {', '.join(missing)}" if missing else "",
        )

    # ── Run ────────────────────────────────────────────────────────────

    def run_all(self) -> list[CheckResult]:
        self._results = [
            self.check_pytest(),
            self.check_mypy(),
            self.check_ruff(),
            self.check_tsc(),
            self.check_feature_list(),
            self.check_checkpoints(),
        ]
        return self._results

    def run_category(self, category: str) -> list[CheckResult]:
        checks = {
            "python": [self.check_pytest, self.check_mypy, self.check_ruff],
            "frontend": [self.check_tsc],
            "repo": [self.check_feature_list, self.check_checkpoints],
            "all": [
                self.check_pytest,
                self.check_mypy,
                self.check_ruff,
                self.check_tsc,
                self.check_feature_list,
                self.check_checkpoints,
            ],
        }
        self._results = [c() for c in checks.get(category, checks["all"])]
        return self._results

    def report(self, results: Optional[list[CheckResult]] = None) -> dict[str, Any]:
        r = results or self._results
        return {
            "passed": all(x.passed for x in r),
            "total": len(r),
            "successful": sum(1 for x in r if x.passed),
            "failed": sum(1 for x in r if not x.passed),
            "checks": [
                {
                    "name": x.name,
                    "passed": x.passed,
                    "duration_ms": x.duration_ms,
                    "output": x.output,
                    "error": x.error,
                    "details": x.details,
                }
                for x in r
            ],
        }

    def print_report(self, results: Optional[list[CheckResult]] = None) -> None:
        r = results or self._results
        print()
        print("#" * 60)
        print("  WORKFLOW VALIDATOR REPORT")
        print("#" * 60)
        for c in r:
            print(f"  {c.summary}")
        print("#" * 60)
        ok = all(x.passed for x in r)
        print(f"  {'[OK] ALL CHECKS PASSED' if ok else '[FAIL] SOME CHECKS FAILED'}")
        print(f"  {sum(1 for x in r if x.passed)}/{len(r)} passed")
        if not ok:
            for c in r:
                if not c.passed:
                    print(f"\n  --- {c.name} output ---")
                    if c.output:
                        for line in c.output.split("\n")[-10:]:
                            print(f"  | {line}")
                    if c.error:
                        print(f"  | ERROR: {c.error}")
        print("#" * 60)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Workflow Validator")
    parser.add_argument("--category", choices=["python", "frontend", "repo", "all"], default="all")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    v = WorkflowValidator()
    results = v.run_category(args.category)
    report = v.report(results)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        v.print_report(results)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
