"""
Workflow Run - Punto de entrada único para el ciclo de desarrollo.

Ejecuta el pipeline completo:
1. Selecciona feature pendiente
2. Corre init.ps1 (pre-flight)
3. Marca in_progress en feature_list.json
4. Implementa (paso delegado al agente/humano)
5. Corre validación completa
6. Si pasa → cierra sesión con commit

Uso:
    python -m workflow.run                    # Próxima feature pendiente
    python -m workflow.run --id F47           # Feature específica
    python -m workflow.run --validate-only     # Solo validación
    python -m workflow.run --status            # Estado actual
"""

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("workflow.run")

ROOT = Path(__file__).parent.parent


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_pre_flight() -> bool:
    """Run init.ps1 as pre-flight check."""
    logger.info("--- Pre-flight: init.ps1 ---")
    ps1 = ROOT / "init.ps1"
    if not ps1.exists():
        logger.error("init.ps1 not found")
        return False
    try:
        r = subprocess.run(
            ["powershell", "-File", str(ps1), "-Quick"], capture_output=True, text=True, timeout=120, cwd=ROOT
        )
        if r.returncode != 0:
            logger.error(f"init.ps1 failed (exit {r.returncode})")
            logger.error(r.stdout[-500:] if r.stdout else r.stderr[-500:])
            return False
        logger.info("init.ps1: OK")
        return True
    except subprocess.TimeoutExpired:
        logger.error("init.ps1 timed out")
        return False


def run_validation() -> dict[str, Any]:
    """Run full validation suite."""
    from workflow.validator import WorkflowValidator

    logger.info("--- Validation ---")
    v = WorkflowValidator()
    results = v.run_all()
    report = v.report(results)
    v.print_report(results)
    return report


def close_session(feature_id: str, report: dict[str, Any], push: bool = False) -> str:
    """Close session: update tracking + commit."""
    from workflow.session import SessionCloser

    logger.info("--- Closing session ---")
    closer = SessionCloser()
    data = _read_json(ROOT / "feature_list.json")
    feat = None
    num = int(feature_id.lstrip("F"))
    for f in data.get("features", []):
        if f["id"] == num:
            feat = f
            break
    if not feat:
        logger.error(f"Feature {feature_id} not found")
        return ""

    feat_info = closer.close_feature(feature_id, "done")
    closer.update_current_md(feat_info, report)
    closer.append_history(feat_info)
    commit_hash = closer.git_commit(feat_info, push=push)
    return commit_hash


def show_status() -> None:
    """Show current project status."""
    data = _read_json(ROOT / "feature_list.json")
    features = data.get("features", [])
    done = sum(1 for f in features if f.get("status") == "done")
    pending = sum(1 for f in features if f.get("status") == "pending")
    in_progress = [f for f in features if f.get("status") == "in_progress"]
    blocked = sum(1 for f in features if f.get("status") == "blocked")

    print(
        f"\nFeatures: {len(features)} total | {done} done | {len(in_progress)} active | {pending} pending | {blocked} blocked"
    )
    if in_progress:
        f = in_progress[0]
        print(f"  Current: F{f['id']} - {f['title']}")
    else:
        # Show first pending
        for f in features:
            if f.get("status") == "pending":
                print(f"  Next: F{f['id']} - {f['title']} ({f.get('area', '?')})")
                break

    # Git status
    r = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, cwd=ROOT)
    changes = len([l for l in r.stdout.split("\n") if l.strip()])
    print(f"  Git: {'[DIRTY] ' + str(changes) + ' files' if changes else '[CLEAN]'}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="SRT2Web Workflow Runner")
    parser.add_argument("--id", help="Feature ID to implement (e.g. F47)")
    parser.add_argument("--validate-only", action="store_true", help="Run validation only")
    parser.add_argument("--status", action="store_true", help="Show status only")
    parser.add_argument("--push", action="store_true", help="Push after commit")
    args = parser.parse_args()

    if args.status:
        show_status()
        return 0

    if args.validate_only:
        report = run_validation()
        return 0 if report["passed"] else 1

    # ── Full cycle ────────────────────────────────────────────────

    # 1. Select feature
    data = _read_json(ROOT / "feature_list.json")
    if args.id:
        num = int(args.id.lstrip("F"))
        feature = next((f for f in data["features"] if f["id"] == num), None)
        if not feature:
            logger.error(f"Feature {args.id} not found")
            return 1
    else:
        feature = next((f for f in data["features"] if f.get("status") == "pending"), None)
        if not feature:
            logger.info("No pending features")
            show_status()
            return 0

    fid = f"F{feature['id']}"
    title = feature.get("title", "")
    logger.info("")
    logger.info(f"{'='*60}")
    logger.info(f"  Feature: {fid} - {title}")
    logger.info(f"  Area: {feature.get('area', '?')}  Priority: {feature.get('priority', '?')}")
    logger.info(f"{'='*60}")
    logger.info("")

    # 2. Pre-flight
    if not run_pre_flight():
        logger.error("Pre-flight failed. Aborting.")
        return 1

    # 3. Mark in_progress
    for f in data["features"]:
        if f["id"] == feature["id"]:
            f["status"] = "in_progress"
            break
    _write_json(ROOT / "feature_list.json", data)
    logger.info(f"{fid}: pending → in_progress")
    logger.info("")

    # 4. IMPLEMENTATION STEP (agent does this)
    # The agent reads AGENTS.md, checks current.md, implements the feature
    logger.info(f"{'='*60}")
    logger.info("  IMPLEMENTATION PHASE")
    logger.info("  Read AGENTS.md + progress/current.md + feature spec")
    logger.info("  Implement the code, then run me again with --validate-only")
    logger.info(f"{'='*60}")
    logger.info("")

    # Print the feature spec
    print()
    print(f"  Feature: {fid} - {title}")
    print(f"  Description: {feature.get('description', 'N/A')}")
    if feature.get("files_to_touch"):
        print(f"  Files: {', '.join(feature['files_to_touch'])}")
    if feature.get("acceptance"):
        print("  Acceptance:")
        for a in feature["acceptance"]:
            print(f"    - {a}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
