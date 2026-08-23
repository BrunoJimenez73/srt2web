#!/usr/bin/env python3
"""
QA Loop — 3 agentes en ciclo hasta estabilidad.

Agentes:
  Tester      -> ejecuta bateria de checks y reporta fallos
  Implementer -> toma siguiente feature pending y aplica fix
  Verifier    -> verifica que el fix no rompa nada y marca done

Uso:
  python scripts/qa_loop.py --once          # una iteracion completa
  python scripts/qa_loop.py --tester-only   # solo fase tester
  python scripts/qa_loop.py --max-iterations 10
  python scripts/qa_loop.py --feature 194   # forzar feature

El loop respeta AGENTS.md: una feature a la vez, init.ps1 verde para done.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
HARNESS_DB = PROJECT_ROOT / "harness.db"


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 180) -> tuple[int, str, str]:
    """Ejecuta comando y captura salida. En Windows usa shell para npm/npx."""
    import shutil

    # En Windows npm/npx son .cmd shims — necesitan shell o ruta completa
    if sys.platform == "win32" and cmd and cmd[0] in ("npm", "npx"):
        cmd = [shutil.which(cmd[0]) or cmd[0]] + cmd[1:]
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            encoding="utf-8",
            errors="replace",
        )
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"TIMEOUT after {timeout}s: {' '.join(cmd)}"
    except Exception as e:
        return 1, "", str(e)


@dataclass
class CheckResult:
    name: str
    passed: bool
    duration_s: float = 0.0
    output: str = ""
    severity: str = "media"

    def to_dict(self):
        return {
            "name": self.name,
            "passed": self.passed,
            "duration_s": round(self.duration_s, 2),
            "severity": self.severity,
        }


@dataclass
class TesterReport:
    checks: list[CheckResult] = field(default_factory=list)
    failures: list[CheckResult] = field(default_factory=list)
    passed: bool = True

    def summary(self) -> str:
        total = len(self.checks)
        ok = sum(1 for c in self.checks if c.passed)
        fail = total - ok
        lines = [
            f"Total checks: {total} | Passed: {ok} | Failed: {fail} | Verdict: {'PASS' if self.passed else 'FAIL'}"
        ]
        for c in self.checks:
            icon = "[OK]" if c.passed else "[FAIL]"
            lines.append(f"  {icon} {c.name} ({c.duration_s:.1f}s) {'-- ' + c.output[:120] if not c.passed else ''}")
        return "\n".join(lines)


# ── Tester ────────────────────────────────────────────────────────────────


def phase_tester(quick: bool = True) -> TesterReport:
    """Ejecuta bateria de verificacion y retorna reporte."""
    print("\n" + "=" * 70)
    print(" [TESTER] Fase de deteccion — ejecutando bateria de checks")
    print("=" * 70)

    checks: list[CheckResult] = []
    start_all = time.time()

    def add_check(name: str, cmd: list[str], severity: str = "media", cwd: Path | None = None, timeout: int = 120):
        t0 = time.time()
        rc, out, err = run(cmd, cwd=cwd, timeout=timeout)
        passed = rc == 0
        output = (out + err).strip()[:2000]
        # Heuristica: algunos checks son informativos (no bloquean)
        checks.append(
            CheckResult(name=name, passed=passed, duration_s=time.time() - t0, output=output, severity=severity)
        )
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {name} ({time.time() - t0:.1f}s)")
        if not passed and output:
            print(f"         {output[:300].replace(chr(10), ' | ')}")

    # Harness health (critico)
    add_check("harness health", [sys.executable, "-m", "harness", "health"], severity="alta")

    # Unit tests (con xdist + basetemp aislado — fix WinError 5 en 11/08)
    if quick:
        add_check(
            "pytest unit (quick)",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit/",
                "-q",
                "--tb=line",
                "-m",
                "not slow",
                "-n",
                "auto",
                "--basetemp",
                ".pytest-qa-temp",
            ],
            severity="alta",
            timeout=180,
        )
    else:
        add_check(
            "pytest unit (full)",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/unit/",
                "-q",
                "--tb=line",
                "-n",
                "auto",
                "--basetemp",
                ".pytest-qa-temp",
            ],
            severity="alta",
            timeout=300,
        )

    # Frontend tests
    add_check(
        "frontend vitest", ["npm", "test", "--", "--run"], cwd=PROJECT_ROOT / "frontend", severity="alta", timeout=120
    )

    # Tipado
    add_check(
        "mypy --strict core/ server/ modules/",
        [sys.executable, "-m", "mypy", "core/", "server/", "modules/", "--strict", "--ignore-missing-imports"],
        severity="media",
        timeout=120,
    )
    add_check("tsc --noEmit", ["npx", "tsc", "--noEmit"], cwd=PROJECT_ROOT / "frontend", severity="media", timeout=60)

    # Lint
    add_check(
        "ruff check",
        [sys.executable, "-m", "ruff", "check", "core/", "modules/", "server/", "--quiet"],
        severity="media",
        timeout=60,
    )
    add_check("eslint", ["npm", "run", "lint", "--silent"], cwd=PROJECT_ROOT / "frontend", severity="media", timeout=60)

    # Build
    add_check(
        "astro build",
        ["npx", "astro", "build", "--silent"],
        cwd=PROJECT_ROOT / "frontend",
        severity="media",
        timeout=120,
    )

    # Stats
    add_check("harness stats", [sys.executable, "-m", "harness", "stats"], severity="baja", timeout=30)

    elapsed = time.time() - start_all
    failures = [c for c in checks if not c.passed]
    # Solo fallos de severidad alta bloquean el loop
    blocking = [c for c in failures if c.severity == "alta"]
    report = TesterReport(checks=checks, failures=failures, passed=len(blocking) == 0)
    print(f"\n[TESTER] Completado en {elapsed:.1f}s — {len(checks) - len(failures)}/{len(checks)} checks OK")
    if blocking:
        print(f"[TESTER] {len(blocking)} fallo(s) BLOQUEANTE(s) detectados:")
        for f in blocking:
            print(f"  - {f.name}")
    elif failures:
        print(f"[TESTER] {len(failures)} fallo(s) no bloqueante(s) (media/baja) — se puede continuar")
    else:
        print("[TESTER] Todo verde — no hay fallos bloqueantes")
    return report


# ── Implementer (placeholder) ─────────────────────────────────────────────


def phase_implementer(report: TesterReport, feature_id: str | None = None) -> str | None:
    """Selecciona siguiente feature y propone implementacion.

    En modo automatico real, aqui se invocaria un subagente con Task.
    Por ahora solo selecciona y deja instrucciones.
    """
    print("\n" + "=" * 70)
    print(" [IMPLEMENTER] Fase de implementacion")
    print("=" * 70)

    if feature_id:
        fid = feature_id
    else:
        rc, out, _ = run([sys.executable, "-m", "harness", "next"])
        # harness next imprime "No pending features." o "F194 ..."
        # Si hay pending, parsear id
        rc2, out2, _ = run([sys.executable, "-m", "harness", "list", "--status=pending"])
        # fallback: listar pending y tomar primero
        if "No pending" in out or not out.strip():
            print("[IMPLEMENTER] No hay features pending — nada que implementar")
            return None
        # Extraer primer id de la lista
        lines = [l for l in out2.splitlines() if "F" in l and "pending" in l.lower() or "[" in l]
        # Si harness list --status=pending falló, intentar parsear next
        if out.strip() and "F" in out:
            # formato típico: "F194 ..." o similar
            import re

            m = re.search(r"F?(\d+)", out)
            if m:
                fid = m.group(1)
            else:
                print(f"[IMPLEMENTER] No se pudo parsear next: {out[:200]}")
                return None
        else:
            import re

            m = re.search(r"F?(\d+)", out2)
            fid = m.group(1) if m else None
            if not fid:
                print("[IMPLEMENTER] No hay pending parseable")
                return None

    # Mostrar feature
    rc, out, _ = run([sys.executable, "-m", "harness", "show", str(fid)])
    print(out[:1500] if out else f"Feature {fid} no encontrada")

    print(f"\n[IMPLEMENTER] Siguiente feature: F{fid}")
    print("[IMPLEMENTER] Instrucciones para el agente implementador:")
    print(f"  1. python -m harness update {fid} status in_progress --agent <nombre>")
    print(f'  2. python -m harness session start --notes "F{fid} ..."')
    print("  3. Implementar fix siguiendo AGENTS.md (una feature a la vez)")
    print("  4. Verificar local: pytest -k <feature> + tsc + ruff")
    print("  5. Dejar que Verifier cierre la feature")
    return str(fid)


# ── Verifier ──────────────────────────────────────────────────────────────


def phase_verifier(feature_id: str | None = None) -> bool:
    """Verifica que la implementacion no rompa nada."""
    print("\n" + "=" * 70)
    print(" [VERIFIER] Fase de verificacion")
    print("=" * 70)

    # Re-ejecutar checks criticos
    checks_ok = True
    for name, cmd, cwd in [
        (
            "pytest unit quick",
            [sys.executable, "-m", "pytest", "tests/unit/", "-q", "--tb=line", "-m", "not slow", "-x"],
            None,
        ),
        (
            "mypy",
            [sys.executable, "-m", "mypy", "core/", "server/", "modules/", "--strict", "--ignore-missing-imports"],
            None,
        ),
        ("tsc", ["npx", "tsc", "--noEmit"], PROJECT_ROOT / "frontend"),
        ("harness health", [sys.executable, "-m", "harness", "health"], None),
    ]:
        rc, out, err = run(cmd, cwd=cwd, timeout=180)
        ok = rc == 0
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            print(f"         {(out + err)[:400].replace(chr(10), ' | ')}")
            checks_ok = False

    if checks_ok:
        print("[VERIFIER] Verificacion PASS")
        if feature_id:
            print(f"[VERIFIER] Para cerrar: python -m harness update {feature_id} status done --agent <nombre>")
            print(f'[VERIFIER]             python -m harness session end <id> --features "{feature_id}" --notes "..."')
    else:
        print("[VERIFIER] Verificacion FAIL — volver a Tester")
    return checks_ok


# ── Orchestrator ──────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="QA Loop 3 agentes")
    parser.add_argument("--once", action="store_true", help="una iteracion Tester->Implementer->Verifier")
    parser.add_argument("--tester-only", action="store_true", help="solo fase tester")
    parser.add_argument("--verifier-only", action="store_true", help="solo fase verifier")
    parser.add_argument("--quick", action="store_true", default=True, help="quick tests (default)")
    parser.add_argument("--full", action="store_true", help="full tests (no --quick)")
    parser.add_argument("--max-iterations", type=int, default=10, help="max iteraciones del loop")
    parser.add_argument("--feature", type=str, default=None, help="forzar feature id")
    parser.add_argument("--json-report", type=str, default=None, help="guardar reporte tester en JSON")
    args = parser.parse_args()

    quick = not args.full

    if args.tester_only:
        report = phase_tester(quick=quick)
        if args.json_report:
            Path(args.json_report).write_text(
                json.dumps([c.to_dict() for c in report.checks], indent=2), encoding="utf-8"
            )
            print(f"\nReporte guardado en {args.json_report}")
        print("\n" + report.summary())
        sys.exit(0 if report.passed else 1)

    if args.verifier_only:
        ok = phase_verifier(feature_id=args.feature)
        sys.exit(0 if ok else 1)

    # Loop completo
    iterations = 1 if args.once else args.max_iterations
    for i in range(iterations):
        print(f"\n{'#' * 70}")
        print(f" ITERACION {i + 1}/{iterations}")
        print(f"{'#' * 70}")

        report = phase_tester(quick=quick)
        if args.json_report:
            Path(args.json_report).write_text(
                json.dumps([c.to_dict() for c in report.checks], indent=2), encoding="utf-8"
            )

        if not report.passed:
            print("\n[LOOP] Tester detecto fallos bloqueantes — Implementer debe corregirlos")
            # Intentar identificar si hay feature que cubra el fallo
            fid = phase_implementer(report, feature_id=args.feature)
            if fid:
                print(f"\n[LOOP] Feature {fid} propuesta — iteracion requiere implementacion manual")
                print("[LOOP] Pausando loop hasta que Implementer complete la feature")
                break
            else:
                print("[LOOP] No hay feature que cubra el fallo — crear nueva feature y reintentar")
                break
        else:
            # No hay fallos bloqueantes — verificar si hay pending features para mejora continua
            rc, out, _ = run([sys.executable, "-m", "harness", "list", "--status=pending"])
            has_pending = "F" in out and "pending" in out.lower() or any(c.isdigit() for c in out)
            # Mejor: chequeo directo
            rc2, out2, _ = run([sys.executable, "-m", "harness", "next"])
            if "No pending" in out2 or not out2.strip():
                print("\n[LOOP] No hay features pending y tester PASS — proyecto ESTABLE")
                print("[LOOP] Loop terminado exitosamente")
                sys.exit(0)
            else:
                print(f"\n[LOOP] Tester PASS pero hay pending: {out2.strip()[:200]}")
                fid = phase_implementer(report, feature_id=args.feature)
                ok = phase_verifier(feature_id=fid)
                if ok:
                    print(f"\n[LOOP] Iteracion {i + 1} completada — continuar a siguiente pending")
                    if args.once:
                        break
                    continue
                else:
                    print(f"\n[LOOP] Verifier FAIL en iteracion {i + 1} — volver a tester")
                    if args.once:
                        break
                    continue

    print("\n[LOOP] Fin de iteraciones")
    print(report.summary() if "report" in locals() else "")


if __name__ == "__main__":
    main()
