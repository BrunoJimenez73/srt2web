"""Parse progress markdown files and import into the database."""

from __future__ import annotations

import re
from pathlib import Path

from .db import HarnessDB
from .models import Progress


def parse_history_md(content: str) -> list[Progress]:
    """Parse progress/history.md into Progress objects."""
    sessions: list[Progress] = []
    # Split by ## headings (sessions)
    sections = re.split(r"^## ", content, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        lines = section.strip().split("\n")
        header = lines[0].strip()

        # Extract date and title from header like "2026-06-23 — F150: PTS-based subtitle sync"
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})\s*[\u2014\u2013-]\s*(.+)", header)
        if not date_match:
            continue

        date = date_match.group(1)
        title = date_match.group(2).strip()

        # Extract feature IDs mentioned
        feature_ids = re.findall(r"[Ff](\d+)", section)
        # Deduplicate and sort
        feature_ids = sorted(set(feature_ids), key=lambda x: int(x))

        # Extract files changed
        files = re.findall(r"`([^`]+\.(?:py|ts|tsx|astro|json|yml|yaml|md|sh|bat))`", section)
        # Also match file paths without backticks
        files += re.findall(r"(?:^|\s)((?:core|modules|server|frontend|cli|tests|docs)/[^\s,]+)", section)
        files = sorted(set(files))

        # Extract verification results
        verification = {}
        check_pattern = re.findall(r"(?:✅|PASS|OK)\s*[:\-]?\s*(.+?)(?:\n|$)", section)
        for check in check_pattern:
            verification[check.strip()] = "PASS"

        sessions.append(
            Progress(
                date=date,
                title=title,
                features_worked=feature_ids,
                files_changed=files,
                verification=verification,
                content_md=section.strip(),
            )
        )

    return sessions


def parse_current_md(content: str) -> Progress | None:
    """Parse progress/current.md into a Progress object."""
    if not content.strip():
        return None

    # Extract session title
    title_match = re.search(
        r"#\s*(?:Sesi[oó]n actual|Current session)\s*[\u2014\u2013-]\s*(.+)", content, re.IGNORECASE
    )
    title = title_match.group(1).strip() if title_match else "Current session"

    # Extract date from title or content
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", content)
    date = date_match.group(1) if date_match else ""

    # Extract feature IDs
    feature_ids = re.findall(r"[Ff](\d+)", content)
    feature_ids = sorted(set(feature_ids), key=lambda x: int(x))

    # Extract files changed
    files = re.findall(r"`([^`]+\.(?:py|ts|tsx|astro|json|yml|yaml|md|sh|bat))`", content)
    files += re.findall(r"(?:^|\s)((?:core|modules|server|frontend|cli|tests|docs)/[^\s,]+)", content)
    files = sorted(set(files))

    # Extract verification table
    verification = {}
    table_rows = re.findall(r"\|\s*(.+?)\s*\|\s*(.+?)\s*\|", content)
    for row_name, status in table_rows:
        if row_name.strip() in ("Check", "---", "------------"):
            continue
        verification[row_name.strip()] = status.strip()

    return Progress(
        date=date,
        title=title,
        features_worked=feature_ids,
        files_changed=files,
        verification=verification,
        content_md=content,
        is_current=True,
    )


def import_progress_from_md(
    db: HarnessDB,
    history_path: str | Path = "progress/history.md",
    current_path: str | Path = "progress/current.md",
) -> dict:
    """Import progress data from markdown files into the database."""
    history_path = Path(history_path)
    current_path = Path(current_path)
    imported = 0
    errors: list[str] = []

    # Import history
    if history_path.exists():
        content = history_path.read_text(encoding="utf-8")
        sessions = parse_history_md(content)
        for session in sessions:
            try:
                db.upsert_progress(session)
                imported += 1
            except Exception as e:
                errors.append(f"Session {session.date}: {e}")

    # Import current
    if current_path.exists():
        content = current_path.read_text(encoding="utf-8")
        current = parse_current_md(content)
        if current:
            try:
                db.upsert_progress(current)
                # Mark as current
                if current.date:
                    existing = db.get_progress_by_date(current.date)
                    if existing and existing.id:
                        db.set_current_progress(existing.id)
                imported += 1
            except Exception as e:
                errors.append(f"Current session: {e}")

    return {
        "imported": imported,
        "errors": errors,
    }


if __name__ == "__main__":
    db = HarnessDB()
    db.connect()
    result = import_progress_from_md(db)
    print(f"Imported: {result['imported']} progress entries")
    for err in result["errors"]:
        print(f"  ERROR: {err}")
    db.close()
