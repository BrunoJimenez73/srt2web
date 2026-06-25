"""SQLite database layer for the harness feature tracking system."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from .models import Feature, Session, AuditEntry, RiskAssessment, Progress

# DB lives at project root: <project>/harness.db
DEFAULT_DB_PATH = Path(__file__).parent.parent / "harness.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS features (
    id                  TEXT PRIMARY KEY,
    name                TEXT NOT NULL,
    title               TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending','in_progress','done','blocked')),
    area                TEXT DEFAULT '',
    priority            TEXT DEFAULT 'Media',
    description         TEXT DEFAULT '',
    problems_identified TEXT DEFAULT '[]',
    acceptance          TEXT DEFAULT '[]',
    files_to_touch      TEXT DEFAULT '[]',
    risk_assessment     TEXT DEFAULT NULL,
    completed_date      TEXT DEFAULT '',
    started_in_session  TEXT DEFAULT '',
    completed_in_session TEXT DEFAULT '',
    dependencies        TEXT DEFAULT '[]',
    phase               TEXT DEFAULT '',
    fix                 TEXT DEFAULT '[]',
    results             TEXT DEFAULT NULL,
    completion_notes    TEXT DEFAULT '',
    created_at          TEXT NOT NULL,
    updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    features_worked TEXT DEFAULT '[]',
    notes           TEXT DEFAULT '',
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    feature_id  TEXT NOT NULL,
    field_name  TEXT NOT NULL,
    old_value   TEXT DEFAULT '',
    new_value   TEXT DEFAULT '',
    agent       TEXT DEFAULT '',
    timestamp   TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_features_status ON features(status);
CREATE INDEX IF NOT EXISTS idx_features_area ON features(area);
CREATE INDEX IF NOT EXISTS idx_features_priority ON features(priority);
CREATE INDEX IF NOT EXISTS idx_audit_feature ON audit_log(feature_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);

CREATE TABLE IF NOT EXISTS progress (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    date            TEXT NOT NULL,
    title           TEXT NOT NULL,
    session_notes   TEXT DEFAULT '',
    features_worked TEXT DEFAULT '[]',
    files_changed   TEXT DEFAULT '[]',
    verification    TEXT DEFAULT '{}',
    content_md      TEXT DEFAULT '',
    is_current      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_progress_date ON progress(date);
CREATE INDEX IF NOT EXISTS idx_progress_current ON progress(is_current);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class HarnessDB:
    """Manages the harness SQLite database."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.executescript(SCHEMA)
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ── Feature CRUD ──────────────────────────────────────────────────

    def get_feature(self, feature_id: int | str) -> Feature | None:
        conn = self.connect()
        row = conn.execute("SELECT * FROM features WHERE id = ?", (str(feature_id),)).fetchone()
        return Feature.from_row(row) if row else None

    def list_features(
        self,
        status: str | None = None,
        area: str | None = None,
        priority: str | None = None,
    ) -> list[Feature]:
        conn = self.connect()
        query = "SELECT * FROM features WHERE 1=1"
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if area:
            query += " AND area = ?"
            params.append(area)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        query += " ORDER BY id"
        rows = conn.execute(query, params).fetchall()
        return [Feature.from_row(r) for r in rows]

    def count_by_status(self) -> dict[str, int]:
        conn = self.connect()
        rows = conn.execute("SELECT status, COUNT(*) as cnt FROM features GROUP BY status").fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    def next_feature(self) -> Feature | None:
        """Return the next feature to work on (highest priority pending)."""
        priority_order = {"Alta": 0, "Media": 1, "Baja": 2}
        pending = self.list_features(status="pending")
        if not pending:
            return None
        pending.sort(key=lambda f: (priority_order.get(f.priority, 1), f.numeric_id))
        return pending[0]

    def upsert_feature(self, feature: Feature, agent: str = "") -> None:
        """Insert or update a feature, logging changes to audit_log."""
        now = _now()
        existing = self.get_feature(feature.id)

        with self.transaction() as conn:
            if existing and agent:
                self._audit_changes(conn, existing, feature, agent)

            created = existing.created_at if existing else now

            conn.execute(
                """INSERT INTO features (id, name, title, status, area, priority, description,
                    problems_identified, acceptance, files_to_touch, risk_assessment,
                    completed_date, started_in_session, completed_in_session,
                    dependencies, phase, fix, results, completion_notes,
                    created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, title=excluded.title, status=excluded.status,
                    area=excluded.area, priority=excluded.priority,
                    description=excluded.description,
                    problems_identified=excluded.problems_identified,
                    acceptance=excluded.acceptance,
                    files_to_touch=excluded.files_to_touch,
                    risk_assessment=excluded.risk_assessment,
                    completed_date=excluded.completed_date,
                    started_in_session=excluded.started_in_session,
                    completed_in_session=excluded.completed_in_session,
                    dependencies=excluded.dependencies,
                    phase=excluded.phase, fix=excluded.fix,
                    results=excluded.results,
                    completion_notes=excluded.completion_notes,
                    created_at=excluded.created_at, updated_at=excluded.updated_at""",
                (
                    str(feature.id),
                    feature.name,
                    feature.title,
                    feature.status,
                    feature.area,
                    feature.priority,
                    feature.description,
                    json.dumps(feature.problems_identified, ensure_ascii=False),
                    json.dumps(feature.acceptance, ensure_ascii=False),
                    json.dumps(feature.files_to_touch, ensure_ascii=False),
                    feature.risk_assessment.to_json() if feature.risk_assessment else None,
                    feature.completed_date,
                    feature.started_in_session,
                    feature.completed_in_session,
                    json.dumps(feature.dependencies, ensure_ascii=False),
                    feature.phase,
                    json.dumps(feature.fix, ensure_ascii=False),
                    json.dumps(feature.results, ensure_ascii=False) if feature.results else None,
                    feature.completion_notes,
                    created,
                    now,
                ),
            )

    def update_feature_field(
        self,
        feature_id: int | str,
        field_name: str,
        value: Any,
        agent: str = "",
    ) -> bool:
        """Update a single field of a feature. Returns True if updated."""
        feature = self.get_feature(feature_id)
        if not feature:
            return False

        old_value = getattr(feature, field_name, None)
        if old_value == value:
            return True

        _json_fields = {
            "problems_identified",
            "acceptance",
            "files_to_touch",
            "fix",
            "dependencies",
            "risk_assessment",
            "results",
        }

        def _serialize(v: Any) -> str:
            if field_name in _json_fields and isinstance(v, (list, dict)):
                return json.dumps(v, ensure_ascii=False)
            return str(v)

        now = _now()
        with self.transaction() as conn:
            if agent:
                conn.execute(
                    "INSERT INTO audit_log (feature_id, field_name, old_value, new_value, agent, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(feature_id), field_name, _serialize(old_value), _serialize(value), agent, now),
                )

            conn.execute(
                f"UPDATE features SET {field_name} = ?, updated_at = ? WHERE id = ?",
                (_serialize(value), now, str(feature_id)),
            )
        return True

    def _audit_changes(
        self,
        conn: sqlite3.Connection,
        old: Feature,
        new: Feature,
        agent: str,
    ) -> None:
        """Log field changes between old and new feature states."""
        now = _now()
        fields_to_check = [
            "status",
            "name",
            "title",
            "area",
            "priority",
            "description",
            "completed_date",
            "started_in_session",
            "completion_notes",
            "phase",
        ]
        for field_name in fields_to_check:
            old_val = str(getattr(old, field_name, ""))
            new_val = str(getattr(new, field_name, ""))
            if old_val != new_val:
                conn.execute(
                    "INSERT INTO audit_log (feature_id, field_name, old_value, new_value, agent, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (str(old.id), field_name, old_val, new_val, agent, now),
                )

    def get_audit_trail(self, feature_id: int | str) -> list[AuditEntry]:
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM audit_log WHERE feature_id = ? ORDER BY timestamp DESC",
            (str(feature_id),),
        ).fetchall()
        return [AuditEntry.from_row(r) for r in rows]

    # ── Sessions ──────────────────────────────────────────────────────

    def start_session(self, notes: str = "") -> Session:
        now = _now()
        date = _today()
        with self.transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (date, features_worked, notes, created_at) VALUES (?, ?, ?, ?)",
                (date, "[]", notes, now),
            )
            row = conn.execute("SELECT last_insert_rowid()").fetchone()
            session_id = row[0]
        return Session(id=session_id, date=date, notes=notes, created_at=now)

    def end_session(self, session_id: int, features_worked: list[str], notes: str = "") -> None:
        now = _now()
        with self.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET features_worked = ?, notes = ? WHERE id = ?",
                (json.dumps(features_worked, ensure_ascii=False), notes, session_id),
            )

    def list_sessions(self, limit: int = 20) -> list[Session]:
        conn = self.connect()
        rows = conn.execute("SELECT * FROM sessions ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
        return [Session.from_row(r) for r in rows]

    # ── Progress ──────────────────────────────────────────────────────

    def upsert_progress(self, progress: Progress) -> None:
        """Insert or update a progress entry."""
        now = _now()
        existing = None
        if progress.id:
            existing = self.get_progress(progress.id)
        if not existing:
            # Check by date
            existing = self.get_progress_by_date(progress.date)

        with self.transaction() as conn:
            created = existing.created_at if existing else now if existing else now
            if existing and existing.created_at:
                created = existing.created_at

            conn.execute(
                """INSERT INTO progress (id, date, title, session_notes, features_worked,
                    files_changed, verification, content_md, is_current, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                    date=excluded.date, title=excluded.title,
                    session_notes=excluded.session_notes,
                    features_worked=excluded.features_worked,
                    files_changed=excluded.files_changed,
                    verification=excluded.verification,
                    content_md=excluded.content_md,
                    is_current=excluded.is_current,
                    updated_at=excluded.updated_at""",
                (
                    existing.id if existing else None,
                    progress.date,
                    progress.title,
                    progress.session_notes,
                    json.dumps(progress.features_worked, ensure_ascii=False),
                    json.dumps(progress.files_changed, ensure_ascii=False),
                    json.dumps(progress.verification, ensure_ascii=False),
                    progress.content_md,
                    1 if progress.is_current else 0,
                    created,
                    now,
                ),
            )

    def get_progress(self, progress_id: int) -> Progress | None:
        conn = self.connect()
        row = conn.execute("SELECT * FROM progress WHERE id = ?", (progress_id,)).fetchone()
        return Progress.from_row(row) if row else None

    def get_progress_by_date(self, date: str) -> Progress | None:
        conn = self.connect()
        row = conn.execute("SELECT * FROM progress WHERE date = ?", (date,)).fetchone()
        return Progress.from_row(row) if row else None

    def get_current_progress(self) -> Progress | None:
        conn = self.connect()
        row = conn.execute("SELECT * FROM progress WHERE is_current = 1 ORDER BY date DESC LIMIT 1").fetchone()
        return Progress.from_row(row) if row else None

    def list_progress(self, limit: int = 30) -> list[Progress]:
        conn = self.connect()
        rows = conn.execute("SELECT * FROM progress ORDER BY date DESC LIMIT ?", (limit,)).fetchall()
        return [Progress.from_row(r) for r in rows]

    def set_current_progress(self, progress_id: int) -> None:
        """Mark one progress entry as current, unset all others."""
        with self.transaction() as conn:
            conn.execute("UPDATE progress SET is_current = 0")
            conn.execute("UPDATE progress SET is_current = 1 WHERE id = ?", (progress_id,))

    # ── Health / Stats ────────────────────────────────────────────────

    def health(self) -> dict[str, Any]:
        """Run health checks and return results."""
        issues: list[str] = []
        stats: dict[str, Any] = {}

        if not self.db_path.exists():
            return {"healthy": False, "issues": ["Database file does not exist"], "stats": {}}

        try:
            conn = self.connect()
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for required in ["features", "sessions", "audit_log", "progress"]:
                if required not in tables:
                    issues.append(f"Missing table: {required}")
        except Exception as e:
            issues.append(f"Schema check failed: {e}")

        try:
            stats["counts_by_status"] = self.count_by_status()
            all_features = self.list_features()
            stats["total_features"] = len(all_features)

            valid_statuses = {"pending", "in_progress", "done", "blocked"}
            for f in all_features:
                if f.status not in valid_statuses:
                    issues.append(f"Feature {f.id} has invalid status: {f.status}")

            in_progress = [f for f in all_features if f.status == "in_progress"]
            if len(in_progress) > 1:
                issues.append(f"{len(in_progress)} features in_progress (max 1)")

            ids = [str(f.id) for f in all_features]
            dupes = [x for x in ids if ids.count(x) > 1]
            if dupes:
                issues.append(f"Duplicate feature IDs: {set(dupes)}")

        except Exception as e:
            issues.append(f"Feature validation failed: {e}")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "stats": stats,
        }

    def export_to_dict(self) -> dict[str, Any]:
        """Export all data to a dict matching the legacy JSON format."""
        features = self.list_features()
        return {
            "project": "srt2web",
            "description": "Sistema de traduccion de subtitulos en tiempo real",
            "rules": {
                "one_feature_at_a_time": True,
                "require_tests_to_close": True,
                "valid_status": ["pending", "in_progress", "done", "blocked"],
            },
            "features": [f.to_dict() for f in features],
        }
