"""SQLite database layer for the harness feature tracking system."""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Agent, AgentFeedback, AgentTask, AuditEntry, Feature, Progress, Session, normalize_id

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

-- Agent System Tables
CREATE TABLE IF NOT EXISTS agents (
    name        TEXT PRIMARY KEY,
    role        TEXT NOT NULL,
    description TEXT DEFAULT '',
    config      TEXT DEFAULT '{}',
    status      TEXT DEFAULT 'idle',
    current_task_id TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_tasks (
    id              TEXT PRIMARY KEY,
    feature_id      TEXT NOT NULL,
    agent_name      TEXT NOT NULL,
    type            TEXT NOT NULL,
    description     TEXT NOT NULL,
    input_data      TEXT DEFAULT '{}',
    output_data     TEXT DEFAULT '{}',
    status          TEXT DEFAULT 'pending',
    iterations      INTEGER DEFAULT 0,
    max_iterations  INTEGER DEFAULT 5,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL,
    completed_at    TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_agent_tasks_feature ON agent_tasks(feature_id);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_agent ON agent_tasks(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_tasks_status ON agent_tasks(status);

CREATE TABLE IF NOT EXISTS agent_feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL,
    approved        INTEGER NOT NULL,
    comments        TEXT DEFAULT '',
    issues          TEXT DEFAULT '[]',
    suggestions     TEXT DEFAULT '[]',
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_feedback_task ON agent_feedback(task_id);
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
            raise ValueError(
                f"Field '{field_name}' not allowed for update (allowlist: {sorted(self._ALLOWED_UPDATE_FIELDS)})"
            )
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

    # ── Agent System ────────────────────────────────────────────────────

    def init_default_agents(self) -> None:
        """Initialize the three default agents: tester, builder, verifier."""
        agents = [
            Agent(
                name="tester",
                role="tester",
                description="Tests the program, finds bugs, suggests improvements, reports failures",
                config={"test_commands": ["pytest tests/unit/", "npm test"], "auto_run": True},
                status="idle",
                created_at=_now(),
                updated_at=_now(),
            ),
            Agent(
                name="builder",
                role="builder",
                description="Implements improvements and fixes based on tester reports",
                config={"auto_apply": False, "require_verification": True},
                status="idle",
                created_at=_now(),
                updated_at=_now(),
            ),
            Agent(
                name="verifier",
                role="verifier",
                description="Verifies builder implementations, approves or sends feedback for rework",
                config={"strict_mode": True, "require_tests_pass": True},
                status="idle",
                created_at=_now(),
                updated_at=_now(),
            ),
        ]
        for agent in agents:
            self.upsert_agent(agent)

    def upsert_agent(self, agent: Agent) -> None:
        """Insert or update an agent."""
        now = _now()
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO agents (name, role, description, config, status, current_task_id, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                    role=excluded.role, description=excluded.description,
                    config=excluded.config, status=excluded.status,
                    current_task_id=excluded.current_task_id, updated_at=excluded.updated_at""",
                (
                    agent.name,
                    agent.role,
                    agent.description,
                    json.dumps(agent.config, ensure_ascii=False),
                    agent.status,
                    agent.current_task_id or "",
                    agent.created_at,
                    now,
                ),
            )

    def get_agent(self, name: str) -> Agent | None:
        """Get an agent by name."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM agents WHERE name = ?", (name,)).fetchone()
        if not row:
            return None
        return Agent(
            name=row["name"],
            role=row["role"],
            description=row["description"] or "",
            config=json.loads(row["config"] or "{}"),
            status=row["status"] or "idle",
            current_task_id=row["current_task_id"] or None,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    def list_agents(self) -> list[Agent]:
        """List all agents."""
        conn = self.connect()
        rows = conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [
            Agent(
                name=row["name"],
                role=row["role"],
                description=row["description"] or "",
                config=json.loads(row["config"] or "{}"),
                status=row["status"] or "idle",
                current_task_id=row["current_task_id"] or None,
                created_at=row["created_at"] or "",
                updated_at=row["updated_at"] or "",
            )
            for row in rows
        ]

    def update_agent_status(self, name: str, status: str, current_task_id: str | None = None) -> bool:
        """Update an agent's status and optionally current task."""
        now = _now()
        with self.transaction() as conn:
            if current_task_id is not None:
                conn.execute(
                    "UPDATE agents SET status = ?, current_task_id = ?, updated_at = ? WHERE name = ?",
                    (status, current_task_id, now, name),
                )
            else:
                conn.execute(
                    "UPDATE agents SET status = ?, updated_at = ? WHERE name = ?",
                    (status, now, name),
                )
        return True

    def create_agent_task(
        self,
        feature_id: str,
        agent_name: str,
        task_type: str,
        description: str,
        input_data: dict[str, Any] | None = None,
        max_iterations: int = 5,
    ) -> AgentTask:
        """Create a new task for an agent."""
        import uuid

        task = AgentTask(
            id=str(uuid.uuid4())[:8],
            feature_id=self._nid(feature_id),
            agent_name=agent_name,
            type=task_type,
            description=description,
            input_data=input_data or {},
            max_iterations=max_iterations,
            created_at=_now(),
            updated_at=_now(),
        )
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO agent_tasks (id, feature_id, agent_name, type, description,
                       input_data, output_data, status, iterations, max_iterations, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    task.id,
                    task.feature_id,
                    task.agent_name,
                    task.type,
                    task.description,
                    json.dumps(task.input_data, ensure_ascii=False),
                    json.dumps(task.output_data, ensure_ascii=False),
                    task.status,
                    task.iterations,
                    task.max_iterations,
                    task.created_at,
                    task.updated_at,
                ),
            )
        return task

    def get_agent_task(self, task_id: str) -> AgentTask | None:
        """Get a task by ID."""
        conn = self.connect()
        row = conn.execute("SELECT * FROM agent_tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            return None
        return AgentTask(
            id=row["id"],
            feature_id=row["feature_id"],
            agent_name=row["agent_name"],
            type=row["type"],
            description=row["description"],
            input_data=json.loads(row["input_data"] or "{}"),
            output_data=json.loads(row["output_data"] or "{}"),
            status=row["status"] or "pending",
            iterations=row["iterations"] or 0,
            max_iterations=row["max_iterations"] or 5,
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
            completed_at=row["completed_at"] or "",
        )

    def list_agent_tasks(
        self,
        feature_id: str | None = None,
        agent_name: str | None = None,
        status: str | None = None,
    ) -> list[AgentTask]:
        """List tasks with optional filters."""
        conn = self.connect()
        query = "SELECT * FROM agent_tasks WHERE 1=1"
        params: list[Any] = []
        if feature_id:
            query += " AND feature_id = ?"
            params.append(self._nid(feature_id))
        if agent_name:
            query += " AND agent_name = ?"
            params.append(agent_name)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [
            AgentTask(
                id=row["id"],
                feature_id=row["feature_id"],
                agent_name=row["agent_name"],
                type=row["type"],
                description=row["description"],
                input_data=json.loads(row["input_data"] or "{}"),
                output_data=json.loads(row["output_data"] or "{}"),
                status=row["status"] or "pending",
                iterations=row["iterations"] or 0,
                max_iterations=row["max_iterations"] or 5,
                created_at=row["created_at"] or "",
                updated_at=row["updated_at"] or "",
                completed_at=row["completed_at"] or "",
            )
            for row in rows
        ]

    def update_agent_task(
        self,
        task_id: str,
        status: str | None = None,
        output_data: dict[str, Any] | None = None,
        iterations: int | None = None,
        input_data: dict[str, Any] | None = None,
    ) -> bool:
        """Update a task's status, input/output data, or iterations."""
        now = _now()
        updates = []
        params: list[Any] = []
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if output_data is not None:
            updates.append("output_data = ?")
            params.append(json.dumps(output_data, ensure_ascii=False))
        if input_data is not None:
            updates.append("input_data = ?")
            params.append(json.dumps(input_data, ensure_ascii=False))
        if iterations is not None:
            updates.append("iterations = ?")
            params.append(iterations)
        updates.append("updated_at = ?")
        params.append(now)
        params.append(task_id)

        if not updates:
            return False

        with self.transaction() as conn:
            conn.execute(f"UPDATE agent_tasks SET {', '.join(updates)} WHERE id = ?", params)
        return True

    def complete_agent_task(self, task_id: str, output_data: dict[str, Any] | None = None) -> bool:
        """Mark a task as completed."""
        now = _now()
        with self.transaction() as conn:
            conn.execute(
                "UPDATE agent_tasks SET status = ?, output_data = ?, updated_at = ?, completed_at = ? WHERE id = ?",
                ("completed", json.dumps(output_data or {}, ensure_ascii=False), now, now, task_id),
            )
        return True

    def save_agent_feedback(
        self,
        task_id: str,
        approved: bool,
        comments: str = "",
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
    ) -> AgentFeedback:
        """Save feedback from verifier to builder."""
        feedback = AgentFeedback(
            task_id=task_id,
            approved=approved,
            comments=comments,
            issues=issues or [],
            suggestions=suggestions or [],
            created_at=_now(),
        )
        with self.transaction() as conn:
            conn.execute(
                """INSERT INTO agent_feedback (task_id, approved, comments, issues, suggestions, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    feedback.task_id,
                    1 if feedback.approved else 0,
                    feedback.comments,
                    json.dumps(feedback.issues, ensure_ascii=False),
                    json.dumps(feedback.suggestions, ensure_ascii=False),
                    feedback.created_at,
                ),
            )
            # Also update task status
            if approved:
                conn.execute(
                    "UPDATE agent_tasks SET status = ?, updated_at = ? WHERE id = ?",
                    ("completed", _now(), task_id),
                )
            else:
                conn.execute(
                    "UPDATE agent_tasks SET status = ?, updated_at = ? WHERE id = ?",
                    ("feedback_received", _now(), task_id),
                )
        return feedback

    def get_feedback_for_task(self, task_id: str) -> list[AgentFeedback]:
        """Get all feedback for a task."""
        conn = self.connect()
        rows = conn.execute(
            "SELECT * FROM agent_feedback WHERE task_id = ? ORDER BY created_at DESC", (task_id,)
        ).fetchall()
        return [
            AgentFeedback(
                task_id=row["task_id"],
                approved=bool(row["approved"]),
                comments=row["comments"] or "",
                issues=json.loads(row["issues"] or "[]"),
                suggestions=json.loads(row["suggestions"] or "[]"),
                created_at=row["created_at"] or "",
            )
            for row in rows
        ]

    def get_latest_feedback(self, task_id: str) -> AgentFeedback | None:
        """Get the most recent feedback for a task."""
        feedbacks = self.get_feedback_for_task(task_id)
        return feedbacks[0] if feedbacks else None

    def get_latest_agent_task(self, feature_id: str, agent_name: str) -> AgentTask | None:
        """Get the most recent task for an agent on a feature."""
        tasks = self.list_agent_tasks(feature_id=feature_id, agent_name=agent_name)
        return tasks[0] if tasks else None

    # ── Phase 1: TESTER ─────────────────────────────────────────────────

    def run_tester_phase(self, feature_id: str, skip_frontend: bool = False) -> dict[str, Any]:
        """Run the tester phase with REAL tests. Creates and completes a test task."""
        feature = self.get_feature(self._nid(feature_id))
        if not feature:
            return {"error": f"Feature {feature_id} not found"}

        self.update_agent_status("tester", "working")
        task = self.create_agent_task(
            feature_id=feature_id,
            agent_name="tester",
            task_type="test",
            description=f"Test feature {feature_id}: {feature.title}",
            input_data={"skip_frontend": skip_frontend},
        )
        try:
            output = self._run_tester_tests(feature_id, skip_frontend=skip_frontend)
        finally:
            self.update_agent_status("tester", "idle")
        self.complete_agent_task(task.id, output)
        return {"task_id": task.id, **output}

    def _run_tester_tests(self, feature_id: str, skip_frontend: bool = False) -> dict[str, Any]:
        """Run the real test suite: pytest unit (+ frontend vitest)."""
        from harness.runner import run_frontend_tests, run_pytest

        root = self.db_path.resolve().parent
        pytest_res = run_pytest(root)
        result: dict[str, Any] = {
            "backend": {k: v for k, v in pytest_res.items() if k != "cmd"},
            "all_passed": pytest_res["all_passed"] and not pytest_res.get("errors"),
            "errors": pytest_res.get("errors", 0),
            "failures": list(pytest_res["failures"]),
        }

        frontend_res: dict[str, Any] | None = None
        if not skip_frontend:
            tester_cfg = self.get_agent("tester")
            run_fe = bool((tester_cfg.config if tester_cfg else {}).get("frontend_tests", True))
            if run_fe:
                frontend_res = run_frontend_tests(root)
                if frontend_res is None:
                    result["frontend"] = {"skipped": True, "reason": "node_modules missing"}
                else:
                    result["frontend"] = {k: v for k, v in frontend_res.items() if k != "cmd"}
                    result["all_passed"] = result["all_passed"] and frontend_res["all_passed"]
                    result["failures"].extend(frontend_res.get("failures", []))

        passed = pytest_res["passed"] + (frontend_res["passed"] if frontend_res else 0)
        failed = pytest_res["failed"] + (frontend_res["failed"] if frontend_res else 0)
        result["tests_run"] = pytest_res["tests_run"] + (
            frontend_res["passed"] + frontend_res["failed"] if frontend_res else 0
        )
        result["passed"] = passed
        result["failed"] = failed
        return result

    # ── Phase 2: BUILDER ────────────────────────────────────────────────

    def open_builder_task(
        self,
        feature_id: str,
        issues: list[str] | None = None,
        suggestions: list[str] | None = None,
        comments: str = "",
    ) -> AgentTask:
        """Create a builder task, or reopen the existing one after a rejection.

        Reuse rule: the latest builder task is reused while it can retry
        (status feedback_received and iterations < max_iterations); otherwise
        a fresh task is created.
        """
        feature = self.get_feature(self._nid(feature_id))
        title = feature.title if feature else feature_id
        latest = self.get_latest_agent_task(self._nid(feature_id), "builder")

        if latest and latest.can_retry:
            history = list(latest.input_data.get("feedback_history", []))
            history.append(
                {
                    "issues": issues or [],
                    "suggestions": suggestions or [],
                    "comments": comments,
                }
            )
            self.update_agent_task(
                latest.id,
                status="pending",
                input_data={
                    "issues": issues or [],
                    "suggestions": suggestions or [],
                    "comments": comments,
                    "feedback_history": history,
                },
            )
            return self.get_agent_task(latest.id)  # type: ignore[return-value]

        return self.create_agent_task(
            feature_id=feature_id,
            agent_name="builder",
            task_type="implement",
            description=f"Fix issues for feature {feature_id}: {title}",
            input_data={
                "issues": issues or [],
                "suggestions": suggestions or [],
                "comments": comments,
                "feedback_history": [],
            },
        )

    # ── Phase 3: VERIFIER ───────────────────────────────────────────────

    def run_verify_phase(self, build_task_id: str, skip_frontend: bool = False) -> dict[str, Any]:
        """Verify a completed builder task with REAL checks.

        - Approved  → feedback(approved=true) recorded against the build task.
        - Rejected  → feedback(issues/suggestions) saved against the build task,
                      iterations+1; task goes to feedback_received for another
                      rework round, or failed when max_iterations is exhausted.
        """
        build_task = self.get_agent_task(build_task_id)
        if not build_task:
            return {"error": f"Task {build_task_id} not found"}
        if build_task.agent_name != "builder" or build_task.type != "implement":
            return {"error": f"Task {build_task_id} is not a builder implement task"}
        if build_task.status not in ("completed",):
            return {
                "error": f"Builder task must be completed before verification (current status: {build_task.status})"
            }
        feature_id = build_task.feature_id

        self.update_agent_status("verifier", "working")
        verify_task = self.create_agent_task(
            feature_id=feature_id,
            agent_name="verifier",
            task_type="verify",
            description=f"Verify fixes for feature {feature_id} (build task {build_task_id})",
            input_data={"build_task_id": build_task_id},
        )
        try:
            checks = self._run_verifier_checks(feature_id, skip_frontend=skip_frontend)
        finally:
            self.update_agent_status("verifier", "idle")
        self.complete_agent_task(verify_task.id, checks)

        approved = bool(checks.get("approved"))
        if approved:
            self.save_agent_feedback(build_task_id, approved=True, comments="All checks passed")
            return {
                "task_id": verify_task.id,
                "build_task_id": build_task_id,
                "approved": True,
                "checks": checks,
            }

        issues = list(checks.get("failures", [])) or ["Verification failed"]
        suggestions = ["Fix the failing checks listed in issues and mark the task completed again"]
        self.save_agent_feedback(
            build_task_id,
            approved=False,
            comments="Verification rejected",
            issues=issues,
            suggestions=suggestions,
        )
        # save_agent_feedback set the build task to feedback_received; now
        # account the iteration and fail it out when the budget is exhausted.
        new_iterations = build_task.iterations + 1
        exhausted = new_iterations >= build_task.max_iterations
        self.update_agent_task(
            build_task_id,
            status="failed" if exhausted else "feedback_received",
            iterations=new_iterations,
        )
        return {
            "task_id": verify_task.id,
            "build_task_id": build_task_id,
            "approved": False,
            "iterations": new_iterations,
            "max_iterations": build_task.max_iterations,
            "exhausted": exhausted,
            "issues": issues,
            "suggestions": suggestions,
            "checks": checks,
        }

    def _run_verifier_checks(self, feature_id: str, skip_frontend: bool = False) -> dict[str, Any]:
        """Re-run the real suite to approve or reject the builder's work."""
        from harness.runner import run_command as _rc
        from harness.runner import run_frontend_tests, run_pytest

        root = self.db_path.resolve().parent
        pytest_res = run_pytest(root)
        failures: list[str] = list(pytest_res["failures"])
        approved = pytest_res["all_passed"]

        frontend_res: dict[str, Any] | None = None
        if not skip_frontend:
            frontend_res = run_frontend_tests(root)
        if frontend_res is not None and not frontend_res["all_passed"]:
            approved = False
            failures.extend(frontend_res.get("failures", []))

        extra_cmds: list[list[str]] = [
            [sys.executable, "-m", "ruff", "check", "harness/"],
        ]
        extra_results = []
        for cmd in extra_cmds:
            res = _rc(cmd, cwd=root)
            extra_results.append({"cmd": cmd, "exit_code": res["exit_code"], "ok": res["exit_code"] == 0})
            if res["exit_code"] != 0:
                approved = False
                failures.append(f"Command failed ({' '.join(cmd)}): see stderr_tail")

        result: dict[str, Any] = {
            "approved": approved,
            "pytest": {k: v for k, v in pytest_res.items() if k != "cmd"},
        }
        if frontend_res is not None:
            result["frontend"] = {k: v for k, v in frontend_res.items() if k != "cmd"}
        elif not skip_frontend:
            result["frontend"] = {"skipped": True, "reason": "node_modules missing"}
        result["extra_commands"] = extra_results
        result["failures"] = failures
        return result

    # ── Full cycle orchestrator ─────────────────────────────────────────

    def run_agent_cycle(
        self,
        feature_id: str,
        max_cycles: int = 5,
        builder_hook: str | None = None,
        skip_frontend: bool = False,
    ) -> dict[str, Any]:
        """Orchestrate tester → builder → verifier until approval.

        Without ``builder_hook`` the cycle stops at ``awaiting_builder`` after
        the first failing test round: an external builder session implements
        the fixes and marks the task completed (``harness agent task complete``),
        then verification runs via ``harness agent verify --task-id X``.

        With ``builder_hook`` (a shell command) the cycle runs fully unattended
        up to ``max_cycles`` rounds. The hook receives HARNESS_TASK_ID in its
        environment and must complete the builder task itself.
        """
        results: dict[str, Any] = {
            "feature_id": feature_id,
            "cycles": [],
            "final_status": "unknown",
        }

        for cycle in range(max_cycles):
            cycle_result: dict[str, Any] = {"cycle": cycle + 1}

            # 1. TESTER — real tests
            test_out = self.run_tester_phase(feature_id, skip_frontend=skip_frontend)
            if "error" in test_out:
                results["final_status"] = "error"
                results["error"] = test_out["error"]
                return results
            cycle_result["test_task_id"] = test_out["task_id"]
            cycle_result["test_result"] = test_out
            results["cycles"].append(cycle_result)

            if test_out.get("all_passed"):
                results["final_status"] = "all_tests_passed"
                return results

            # 2. BUILDER — open/reopen task with the failure report attached
            build_task = self.open_builder_task(
                feature_id,
                issues=test_out.get("failures", []),
                suggestions=[],
                comments=f"Failing tests reported by tester (cycle {cycle + 1})",
            )
            cycle_result["build_task_id"] = build_task.id
            self.update_agent_status("builder", "working", current_task_id=build_task.id)

            if not builder_hook:
                results["final_status"] = "awaiting_builder"
                results["build_task_id"] = build_task.id
                return results

            # External hook does the implementation work
            from harness.runner import run_shell_command

            hook_res = run_shell_command(
                builder_hook, cwd=self.db_path.resolve().parent, env={"HARNESS_TASK_ID": build_task.id}
            )
            cycle_result["hook_result"] = {k: v for k, v in hook_res.items()}
            refreshed = self.get_agent_task(build_task.id)
            if not refreshed or refreshed.status != "completed":
                results["final_status"] = "awaiting_builder_manual"
                results["build_task_id"] = build_task.id
                return results
            self.update_agent_status("builder", "idle")

            # 3. VERIFIER — real checks, feedback loop on rejection
            verify_out = self.run_verify_phase(build_task.id, skip_frontend=skip_frontend)
            if "error" in verify_out:
                results["final_status"] = "error"
                results["error"] = verify_out["error"]
                return results
            cycle_result["verify_result"] = verify_out

            if verify_out.get("approved"):
                results["final_status"] = "approved"
                return results

            if cycle == max_cycles - 1:
                results["final_status"] = "max_cycles_reached"
                results["build_task_id"] = build_task.id

        return results
