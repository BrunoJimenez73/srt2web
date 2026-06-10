"""
F112: Generate or refresh secrets in .env from .env.example.

Behavior:
  - If .env does not exist, copy it from .env.example.
  - For each line in .env matching `KEY=`, if the value is empty or matches
    a known placeholder ('your-secret-token-here', 'change-me-in-production'),
    replace it with a fresh `secrets.token_urlsafe(32)`.
  - Print a short status line (machine-parseable, e.g. "GENERATED: KEY") so
    the calling shell script can react.

Exit codes:
  0 - success
  1 - .env.example missing
  2 - .env not writable
  3 - generation failed for some reason

Usage from shell:
  python scripts/generate_env_secrets.py [--quiet] [--key KEY1 KEY2 ...]
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from pathlib import Path

PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "your-secret-token-here",
        "your-secret-key-here",
        "change-me-in-production",
    }
)

# Keys we own (F112). Adding more here is the only edit needed for new env vars.
MANAGED_KEYS = ("SRT2WEB_JWT_SECRET",)


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _generate_value(key: str) -> str:
    """Generate a secure value for the given key. Currently all are 32-byte urlsafe."""
    return secrets.token_urlsafe(32)


def _ensure_env_file(env_path: Path, example_path: Path) -> str:
    """Make sure .env exists. Returns 'created' or 'exists'."""
    if env_path.exists():
        return "exists"
    if not example_path.exists():
        print(f"ERROR: {example_path} not found; cannot bootstrap {env_path}", file=sys.stderr)
        sys.exit(1)
    env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
    return "created"


def _process_env(env_path: Path, keys: tuple[str, ...], quiet: bool) -> list[str]:
    """Process .env, replacing placeholders. Returns list of generated keys."""
    try:
        original = env_path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot read {env_path}: {e}", file=sys.stderr)
        sys.exit(2)

    generated: list[str] = []
    new_lines: list[str] = []
    for line in original.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not keys or key in keys:
            if value.strip() in PLACEHOLDER_VALUES:
                new_value = _generate_value(key)
                new_lines.append(f"{key}={new_value}")
                generated.append(key)
                continue
        new_lines.append(line)

    try:
        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except OSError as e:
        print(f"ERROR: cannot write {env_path}: {e}", file=sys.stderr)
        sys.exit(2)

    if not quiet:
        for k in generated:
            print(f"GENERATED: {k}")
        if not generated:
            print("KEPT: all keys already configured")
    return generated


def main() -> int:
    parser = argparse.ArgumentParser(description="F112 secret bootstrap for .env")
    parser.add_argument("--quiet", action="store_true", help="Suppress per-key output")
    parser.add_argument(
        "--key",
        nargs="*",
        default=None,
        help="Only process these keys (default: MANAGED_KEYS)",
    )
    parser.add_argument(
        "--env",
        default=str(_project_root() / ".env"),
        help="Path to .env (default: project root .env)",
    )
    parser.add_argument(
        "--example",
        default=str(_project_root() / ".env.example"),
        help="Path to .env.example (default: project root .env.example)",
    )
    args = parser.parse_args()

    env_path = Path(args.env).resolve()
    example_path = Path(args.example).resolve()

    status = _ensure_env_file(env_path, example_path)
    keys = tuple(args.key) if args.key else MANAGED_KEYS
    _process_env(env_path, keys, args.quiet)

    if not args.quiet:
        if status == "created":
            print(f"CREATED: {env_path}")
        else:
            print(f"EXISTS: {env_path}")

    return 0


if __name__ == "__main__":
    # Ensure the venv python is used (shebang), but allow direct invocation
    sys.exit(main())
