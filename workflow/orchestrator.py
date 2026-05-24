"""
Workflow Orchestrator - Ciclo completo de desarrollo.

Flujo:
1. Lee feature_list.json → selecciona feature pending
2. Corre init.ps1 (pre-flight)
3. Ejecuta la feature (guía al agente)
4. Corre validación completa (pytest + mypy + tsc + ruff + checkpoints)
5. Si falla → reporta errores
6. Si pasa → cierra sesión (tracking + commit)

Uso:
    python -m workflow.orchestrator run           # ciclo completo
    python -m workflow.orchestrator run --id F47  # feature específica
    python -m workflow.orchestrator validate       # solo validación
    python -m workflow.orchestrator status         # estado actual
"""

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("workflow.orchestrator")

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class CycleResult:
    passed: bool = False
    feature_id: str = ""
    feature_title: str = ""
    validation_report: Optional[dict[str, Any]] = None
    commit_hash: str = ""
    errors: list[str] = field(default_factory=list)
    duration_sec: float = 0.0


class DevelopmentOrchestrator:
    """Orquestador del ciclo de desarrollo feature→validación→cierre."""

    def __init__(self) -> None:
        self._start_time = 0.0

    # ── Step 1: Select Feature ──────────────────────────────────────────

    def _load_feature_list(self) -> dict[str, Any]:
        path = ROOT / "feature_list.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_feature_list(self, data: dict[str, Any]) -> None:
        path = ROOT / "feature_list.json"
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def select_feature(self, feature_id: Optional[str] = None) -> Optional[dict[str, Any]]:
        """Select the next feature to implement."""
        data = self._load_feature_list()

        if feature_id:
            num = int(feature_id.lstrip("F"))
            for f in data.get("features", []):
                if f.get("id") == num:
                    return f
            logger.error(f"Feature '{feature_id}' not found")
            return None

        # Find first pending feature
        for f in data.get("features", []):
            if f.get("status") == "pending":
                return f

        logger.info("No pending features found")
        return None

    def mark_in_progress(self, feature: dict[str, Any]) -> None:
        """Mark a feature as in_progress."""
        data = self._load_feature_list()
        for f in data.get("features", []):
            if f["id"] == feature["id"]:
                f["status"] = "in_progress"
                break
        self._save_feature_list(data)
        logger.info(f"F{feature['id']} → in_progress")

    # ── Step 2: Pre-flight ──────────────────────────────────────────────

    def pre_flight(self) -> bool:
        """Run pre-flight checks before starting work."""
        logger.info("Running pre-flight checks...")
        required = ["AGENTS.md", "CHECKPOINTS.md", "feature_list.json", "init.ps1"]
        missing = [f for f in required if not (ROOT / f).exists()]
        if missing:
            logger.error(f"Pre-flight failed: missing {missing}")
            return False
        logger.info("Pre-flight OK")
        return True

    # ── Step 3: Validate ────────────────────────────────────────────────

    def validate(self) -> dict[str, Any]:
        """Run full validation suite."""
        from workflow.validator import WorkflowValidator

        logger.info("Running validation suite...")
        v = WorkflowValidator()
        results = v.run_all()
        report = v.report(results)
        v.print_report(results)
        return report

    # ── Step 4: Close Session ───────────────────────────────────────────

    def close_session(self, feature: dict[str, Any], report: dict[str, Any], push: bool = False) -> str:
        """Close the session: update tracking + commit."""
        from workflow.session import SessionCloser

        closer = SessionCloser()
        feat_info = closer.close_feature(f"F{feature['id']}", "done")
        closer.update_current_md(feat_info, report)
        closer.append_history(feat_info)
        commit_hash = closer.git_commit(feat_info, push=push)
        return commit_hash

    # ── Main Cycle ──────────────────────────────────────────────────────

    def run(self, feature_id: Optional[str] = None, push: bool = False) -> CycleResult:
        """Run the complete development cycle."""
        self._start_time = time.time()
        result = CycleResult()

        # 1. Select feature
        feature = self.select_feature(feature_id)
        if feature is None:
            result.errors.append("No feature selected")
            return result

        result.feature_id = f"F{feature['id']}"
        result.feature_title = feature.get("title", "")
        logger.info(f"Selected: {result.feature_id} - {result.feature_title}")

        # 2. Pre-flight
        if not self.pre_flight():
            result.errors.append("Pre-flight checks failed")
            return result

        # 3. Mark in_progress
        self.mark_in_progress(feature)

        # 4. Validate (this is where the agent would implement the feature)
        # In an automated workflow, the implementation step would go here.
        # For now, validation is the main check.
        report = self.validate()
        result.validation_report = report

        # 5. Close or report failure
        if report["passed"]:
            commit_hash = self.close_session(feature, report, push=push)
            result.passed = True
            result.commit_hash = commit_hash
            logger.info(f"✅ Cycle complete: {result.feature_id} → {commit_hash or '(no changes)'}")
        else:
            # Mark as blocked
            data = self._load_feature_list()
            for f in data.get("features", []):
                if f["id"] == feature["id"]:
                    f["status"] = "blocked"
                    break
            self._save_feature_list(data)
            result.errors.append("Validation failed")
            logger.error(f"❌ Validation failed for {result.feature_id}")

        result.duration_sec = time.time() - self._start_time
        return result


def print_status() -> None:
    """Print current project status."""
    from workflow.session import SessionCloser

    s = SessionCloser().status()
    print(
        f"\nFeatures: {s['total_features']} total | {s['done']} done | "
        f"{s['in_progress']} in_progress | {s['pending']} pending"
    )
    if s["current"]:
        c = s["current"]
        print(f"Current: F{c['id']} - {c['title']} ({c['status']})")
    print(f"Git: {'[CHANGED] ' + str(s['git_changes_count']) + ' files' if s['git_changes'] else '[CLEAN]'}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Development Workflow Orchestrator")
    sub = parser.add_subparsers(dest="command")

    run_cmd = sub.add_parser("run", help="Run complete development cycle")
    run_cmd.add_argument("--id", help="Feature ID (e.g. F47)")
    run_cmd.add_argument("--push", action="store_true", help="Push after commit")

    sub.add_parser("validate", help="Run validation suite only")
    sub.add_parser("status", help="Show project status")

    args = parser.parse_args()
    orch = DevelopmentOrchestrator()

    if args.command == "run":
        result = orch.run(feature_id=args.id, push=args.push)
        print(f"\nDuration: {result.duration_sec:.1f}s")
        if result.passed:
            print(f"[OK] {result.feature_id} completed: {result.commit_hash or 'OK'}")
        else:
            print(f"[FAIL] {result.feature_id} failed: {'; '.join(result.errors)}")
        return 0 if result.passed else 1

    elif args.command == "validate":
        report = orch.validate()
        return 0 if report["passed"] else 1

    elif args.command == "status":
        print_status()
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
