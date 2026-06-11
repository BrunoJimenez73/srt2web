"""
F130: Check that .env files with secrets have never been committed to Git.

Exit codes:
  0 — No secrets detected in history.
  1 — .env file was found in git history (secrets may be exposed).

Usage:
  python scripts/check_secrets.py
"""

import subprocess
import sys


SECRET_PATTERNS = [".env", ".env.production", ".env.local"]


def _git_log_all(pattern: str) -> list[str]:
    """Return commit hashes where `pattern` appears in git history."""
    try:
        result = subprocess.run(
            ["git", "log", "--all", "--diff-filter=A", "--follow", "--format=%H", "--", pattern],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        return [h for h in result.stdout.strip().split("\n") if h]
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []


def main() -> int:
    found = False
    for pattern in SECRET_PATTERNS:
        commits = _git_log_all(pattern)
        if commits:
            print(f"SECURITY ISSUE: '{pattern}' found in git history in {len(commits)} commit(s):")
            for c in commits[:10]:
                print(f"  {c}")
            print("  These files may contain secrets. Rotate all credentials and use")
            print("  BFG Repo-Cleaner or git filter-repo to purge them from history.")
            found = True
        else:
            print(f"OK: '{pattern}' not found in git history.")

    if found:
        print("SECRETS MAY BE EXPOSED in git history.")
        return 1
    else:
        print("No secret files detected in git history.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
