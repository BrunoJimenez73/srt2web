"""SQLite database layer for the harness feature tracking system."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import AuditEntry, Feature, Progress, Session, normalize_id

logger = logging.getLogger("srt2web.harness.db")

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
    return datetime.now(UTC).isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


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
        except Exception as e:
            logger.debug("Transaction failed, rolling back: %s", e)
            conn.rollback()
            raise

    # ── Feature CRUD ──────────────────────────────────────────────────

    @staticmethod
    def _nid(feature_id: int | str) -> str:
        """Normalize a feature ID for DB queries."""
        return normalize_id(feature_id)

    def get_feature(self, feature_id: int | str) -> Feature | None:
        conn = self.connect()
        normalized = self._nid(feature_id)
        row = conn.execute("SELECT * FROM features WHERE id = ?", (normalized,)).fetchone()
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

    _ALLOWED_UPDATE_FIELDS: frozenset[str] = frozenset(
        {
            "name",
            "title",
            "status",
            "area",
            "priority",
            "description",
            "problems_identified",
            "acceptance",
            "files_to_touch",
            "risk_assessment",
            "completed_date",
            "started_in_session",
            "completed_in_session",
            "dependencies",
            "phase",
            "fix",
            "results",
            "completion_notes",
        }
    )

    def update_feature_field(
        self,
        feature_id: int | str,
        field_name: str,
        value: Any,
        agent: str = "",
    ) -> bool:
        """Update a single field of a feature. Returns True if updated."""
        if field_name not in self._ALLOWED_UPDATE_FIELDS:
            raise ValueError(f"Field '{field_name}' not allowed for update (allowlist: {sorted(self._ALLOWED_UPDATE_FIELDS)})")
        normalized_id = self._nid(feature_id)
        feature = self.get_feature(normalized_id)
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
                    (normalized_id, field_name, _serialize(old_value), _serialize(value), agent, now),
                )

            conn.execute(
                f"UPDATE features SET {field_name} = ?, updated_at = ? WHERE id = ?",
                (_serialize(value), now, normalized_id),
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
            (self._nid(feature_id),),
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
            created = existing.created_at if existing and existing.created_at else now

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

    # ── Sanitize / Migrate ────────────────────────────────────────────

    def sanitize_ids(self, agent: str = "migrate") -> dict[str, Any]:
        """Sanitize feature IDs: merge duplicates where '115' and 'F115' coexist.

        Returns a summary of actions taken.
        """
        conn = self.connect()
        actions: dict[str, Any] = {"merged": 0, "deleted": 0, "errors": []}
        now = _now()

        # Find all rows whose normalized IDs collide
        rows = conn.execute(
            "SELECT id, name, title, status, area, priority, description, "
            "problems_identified, acceptance, files_to_touch, risk_assessment, "
            "completed_date, started_in_session, completed_in_session, "
            "dependencies, phase, fix, results, completion_notes, "
            "created_at, updated_at FROM features"
        ).fetchall()

        groups: dict[str, list[sqlite3.Row]] = {}
        for row in rows:
            nid = normalize_id(row["id"])
            groups.setdefault(nid, []).append(row)

        for nid, group in groups.items():
            if len(group) < 2:
                continue
            # Prefer the entry with the richer data (longer title, more fields filled)
            group.sort(key=lambda r: len(r["title"] or ""), reverse=True)
            keeper = group[0]
            for duplicate in group[1:]:
                old_id = duplicate["id"]
                try:
                    # Merge non-empty fields from duplicate into keeper
                    fields_to_merge = [
                        "name",
                        "title",
                        "description",
                        "area",
                        "priority",
                        "status",
                        "completed_date",
                        "started_in_session",
                        "completed_in_session",
                        "phase",
                        "completion_notes",
                    ]
                    for field in fields_to_merge:
                        dup_val = duplicate[field]
                        keep_val = keeper[field]
                        if dup_val and not keep_val:
                            conn.execute(
                                f"UPDATE features SET {field} = ?, updated_at = ? WHERE id = ?",
                                (dup_val, now, keeper["id"]),
                            )

                    # Merge JSON list fields
                    for field in ("problems_identified", "acceptance", "files_to_touch", "fix", "dependencies"):
                        dup_list = json.loads(duplicate[field] or "[]")
                        keep_list = json.loads(keeper[field] or "[]")
                        merged = keep_list + [x for x in dup_list if x not in keep_list]
                        conn.execute(
                            f"UPDATE features SET {field} = ?, updated_at = ? WHERE id = ?",
                            (json.dumps(merged, ensure_ascii=False), now, keeper["id"]),
                        )

                    # Remove the duplicate row
                    conn.execute("DELETE FROM features WHERE id = ?", (old_id,))
                    conn.execute(
                        "INSERT INTO audit_log (feature_id, field_name, old_value, new_value, agent, timestamp) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (nid, "id", old_id, f"merged_into_{keeper['id']}", agent, now),
                    )
                    actions["merged"] += 1
                    conn.commit()
                except Exception as e:
                    actions["errors"].append(f"Failed to merge {old_id}: {e}")
                    conn.rollback()

        # Clean up any remaining non-normalized IDs (like 'F115' without a '115' counterpart)
        rows = conn.execute("SELECT id FROM features").fetchall()
        for row in rows:
            raw_id = row["id"]
            nid = normalize_id(raw_id)
            if raw_id != nid:
                try:
                    conn.execute("UPDATE features SET id = ? WHERE id = ?", (nid, raw_id))
                    conn.commit()
                except sqlite3.IntegrityError:
                    # Target already exists, skip (normalized collision already handled above)
                    conn.rollback()

        return actions

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

            # Check for non-normalized IDs (e.g., 'F115' instead of '115')
            raw_ids_from_db = [r[0] for r in conn.execute("SELECT id FROM features").fetchall()]
            for raw_id in raw_ids_from_db:
                if raw_id != normalize_id(raw_id):
                    issues.append(f"Non-normalized feature ID: '{raw_id}' (should be '{normalize_id(raw_id)}')")

            # Check for semantic duplicates (different db rows with same normalized ID)
            normalized_ids = [normalize_id(x) for x in raw_ids_from_db]
            seen: set[str] = set()
            for nid in normalized_ids:
                if nid in seen:
                    issues.append(f"Semantic duplicate: multiple entries with normalized ID '{nid}'")
                seen.add(nid)

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
