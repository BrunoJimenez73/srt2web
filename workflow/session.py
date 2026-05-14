"""
Workflow Session - Cierra una sesión de desarrollo automáticamente.

Actualiza feature_list.json, progress/current.md, progress/history.md,
y hace commit con mensaje generado automáticamente.

Uso:
    python -m workflow.session close --feature F34 --status done
    python -m workflow.session close --feature F35 --status done --push
    python -m workflow.session status              # mostrar estado actual
"""

import json
import logging
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("workflow.session")

ROOT = Path(__file__).parent.parent


@dataclass
class FeatureInfo:
    id: int
    name: str
    title: str
    area: str
    priority: str

    @property
    def feature_id_str(self) -> str:
        return f"F{self.id}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_feature_list() -> dict[str, Any]:
    return _read_json(ROOT / "feature_list.json")


def _write_feature_list(data: dict[str, Any]) -> None:
    _write_json(ROOT / "feature_list.json", data)


def _find_feature(data: dict[str, Any], feature_id: str) -> Optional[dict[str, Any]]:
    """Find feature by id string like 'F34' or integer."""
    if feature_id.startswith("F"):
        num = int(feature_id[1:])
    else:
        num = int(feature_id)
    for f in data.get("features", []):
        if f.get("id") == num:
            return f
    return None


def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + list(args), capture_output=True, text=True, cwd=ROOT, check=check)


class SessionCloser:
    """Automatiza el cierre de sesión: tracking + commit."""

    def close_feature(self, feature_id: str, status: str = "done") -> FeatureInfo:
        """Actualiza el status de una feature en feature_list.json."""
        data = _read_feature_list()
        feature = _find_feature(data, feature_id)
        if feature is None:
            raise ValueError(f"Feature '{feature_id}' not found in feature_list.json")

        old_status = feature.get("status", "unknown")
        feature["status"] = status
        _write_feature_list(data)
        logger.info(f"Feature {feature_id}: {old_status} → {status}")
        return FeatureInfo(
            id=feature["id"],
            name=feature.get("name", ""),
            title=feature.get("title", ""),
            area=feature.get("area", ""),
            priority=feature.get("priority", "Media"),
        )

    def update_current_md(self, feature: FeatureInfo, report: Optional[dict[str, Any]] = None) -> None:
        """Actualiza progress/current.md con el estado de la sesión."""
        path = ROOT / "progress" / "current.md"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"# Sesión activa — {now.split()[0]}",
            "",
            f"**Estado:** {feature.feature_id_str} — {feature.title} completada",
            f"**Iniciada:** {now.split()[0]}",
            "",
            f"## {feature.feature_id_str} — {feature.title} ✅ COMPLETED",
            "",
            f"**Feature**: {feature.feature_id_str} - {feature.title}",
            f"**Status**: done ({now.split()[0]})",
            f"**Área**: {feature.area}",
            "",
        ]
        if report:
            lines.append("### Validation Report")
            lines.append("")
            lines.append(f"| Check | Result |")
            lines.append(f"|-------|--------|")
            for c in report.get("checks", []):
                emoji = "✅" if c["passed"] else "❌"
                lines.append(f"| {c['name']} | {emoji} ({c['duration_ms']:.0f}ms) |")
            lines.append("")
            if report["passed"]:
                lines.append("✅ Todos los checks pasaron.")
            else:
                lines.append("❌ Algunos checks fallaron — revisar antes de continuar.")

        lines.append("")
        lines.append("--- Pendientes para próxima sesión ---")
        lines.append("")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info(f"Updated {path}")

    def append_history(self, feature: FeatureInfo, commit_hash: str = "", files_count: int = 0) -> None:
        """Append entrada a progress/history.md."""
        path = ROOT / "progress" / "history.md"
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = (
            f"\n## {now} — {feature.feature_id_str} {feature.name}\n\n"
            f"- **Feature:** {feature.feature_id_str} - {feature.title}\n"
            f"- **Área:** {feature.area} | **Prioridad:** {feature.priority}\n"
        )
        if commit_hash:
            entry += f"- **Commit:** {commit_hash}\n"
        if files_count:
            entry += f"- **Archivos:** {files_count} cambiados\n"
        entry += f"- **Status:** ✅ done\n"

        with open(path, "a", encoding="utf-8") as f:
            f.write(entry)
        logger.info(f"Appended to {path}")

    def git_commit(self, feature: FeatureInfo, push: bool = False) -> str:
        """Hace commit de los cambios con mensaje automático."""
        # Git add
        _git("add", "-A")

        # Check if there's anything to commit
        status = _git("status", "--porcelain")
        if not status.stdout.strip():
            logger.info("No changes to commit")
            return ""

        # Build message
        msg = f"feat({feature.name}): {feature.title}"
        area_tag = f"[{feature.area}]" if feature.area else ""
        full_msg = f"{msg} {area_tag}" if area_tag else msg

        result = _git("commit", "--no-verify", "-m", full_msg)
        logger.info(f"Committed: {full_msg}")

        # Extract hash
        log = _git("log", "-1", "--oneline")
        commit_hash = log.stdout.strip().split()[0] if log.stdout.strip() else ""

        if push and commit_hash:
            _git("push")
            logger.info("Pushed to origin")

        return commit_hash

    def status(self) -> dict[str, Any]:
        """Muestra el estado actual del repo y features."""
        data = _read_feature_list()
        features = data.get("features", [])
        in_progress = [f for f in features if f.get("status") == "in_progress"]
        pending = [f for f in features if f.get("status") == "pending"]
        done = [f for f in features if f.get("status") == "done"]

        git_status = _git("status", "--porcelain").stdout.strip()

        return {
            "total_features": len(features),
            "in_progress": len(in_progress),
            "pending": len(pending),
            "done": len(done),
            "current": in_progress[0] if in_progress else None,
            "git_changes": bool(git_status),
            "git_changes_count": len([l for l in git_status.split("\n") if l.strip()]),
        }


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Workflow Session Manager")
    sub = parser.add_subparsers(dest="command")

    close = sub.add_parser("close", help="Close a feature session")
    close.add_argument("--feature", required=True, help="Feature ID (e.g. F47)")
    close.add_argument("--status", default="done", choices=["done", "blocked"])
    close.add_argument("--push", action="store_true", help="Push after commit")
    close.add_argument("--skip-commit", action="store_true", help="Skip git commit")

    sub.add_parser("status", help="Show current session status")

    args = parser.parse_args()

    closer = SessionCloser()

    if args.command == "close":
        try:
            feature = closer.close_feature(args.feature, args.status)
            closer.update_current_md(feature)
            closer.append_history(feature)
            if not args.skip_commit:
                commit_hash = closer.git_commit(feature, push=args.push)
                if commit_hash:
                    print(f"\n✅ Session closed: {feature.feature_id_str} → {commit_hash}")
                else:
                    print(f"\n✅ Session closed: {feature.feature_id_str} (no changes)")
            else:
                print(f"\n✅ Session closed: {feature.feature_id_str} (commit skipped)")
        except ValueError as e:
            logger.error(f"Error: {e}")
            return 1

    elif args.command == "status":
        s = closer.status()
        print(f"\nFeatures: {s['total_features']} total | {s['done']} done | "
              f"{s['in_progress']} in_progress | {s['pending']} pending")
        if s["current"]:
            print(f"Current: F{s['current']['id']} - {s['current']['title']} ({s['current']['status']})")
        print(f"Git changes: {'yes (' + str(s['git_changes_count']) + ' files)' if s['git_changes'] else 'clean'}")
    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
