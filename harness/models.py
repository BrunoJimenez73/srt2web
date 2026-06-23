"""Data models for the harness feature tracking system."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional


@dataclass
class RiskAssessment:
    risk_level: str = "Baja"
    mitigation: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str | None) -> RiskAssessment | None:
        if not raw:
            return None
        try:
            d = json.loads(raw)
            return cls(risk_level=d.get("risk_level", "Baja"), mitigation=d.get("mitigation", []))
        except (json.JSONDecodeError, TypeError):
            return None

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> RiskAssessment | None:
        if not d:
            return None
        return cls(risk_level=d.get("risk_level", "Baja"), mitigation=d.get("mitigation", []))


@dataclass
class Feature:
    id: int | str
    name: str
    title: str
    status: str = "pending"
    area: str = ""
    priority: str = "Media"
    description: str = ""
    problems_identified: list[str] = field(default_factory=list)
    acceptance: list[str] = field(default_factory=list)
    files_to_touch: list[str] = field(default_factory=list)
    risk_assessment: RiskAssessment | None = None
    completed_date: str = ""
    started_in_session: str = ""
    completed_in_session: str = ""
    dependencies: list[str] = field(default_factory=list)
    phase: str = ""
    fix: list[str] = field(default_factory=list)
    results: dict[str, Any] | None = None
    completion_notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @property
    def is_done(self) -> bool:
        return self.status == "done"

    @property
    def is_pending(self) -> bool:
        return self.status == "pending"

    @property
    def is_in_progress(self) -> bool:
        return self.status == "in_progress"

    @property
    def is_blocked(self) -> bool:
        return self.status == "blocked"

    @property
    def numeric_id(self) -> int:
        """Extract numeric part from id (handles 'F115' -> 115)."""
        if isinstance(self.id, int):
            return self.id
        s = str(self.id).lstrip("Ff")
        try:
            return int(s)
        except ValueError:
            return 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["risk_assessment"] = asdict(self.risk_assessment) if self.risk_assessment else None
        return d

    @classmethod
    def from_row(cls, row: Any) -> Feature:
        """Create Feature from a sqlite3.Row."""
        risk = RiskAssessment.from_json(row["risk_assessment"]) if row["risk_assessment"] else None
        return cls(
            id=row["id"],
            name=row["name"],
            title=row["title"],
            status=row["status"],
            area=row["area"] or "",
            priority=row["priority"] or "Media",
            description=row["description"] or "",
            problems_identified=json.loads(row["problems_identified"] or "[]"),
            acceptance=json.loads(row["acceptance"] or "[]"),
            files_to_touch=json.loads(row["files_to_touch"] or "[]"),
            risk_assessment=risk,
            completed_date=row["completed_date"] or "",
            started_in_session=row["started_in_session"] or "",
            completed_in_session=row["completed_in_session"] or "",
            dependencies=json.loads(row["dependencies"] or "[]"),
            phase=row["phase"] or "",
            fix=json.loads(row["fix"] or "[]"),
            results=json.loads(row["results"]) if row["results"] else None,
            completion_notes=row["completion_notes"] or "",
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )

    @classmethod
    def from_json_dict(cls, d: dict[str, Any]) -> Feature:
        """Import from the legacy feature_list.json format."""
        risk = RiskAssessment.from_dict(d.get("risk_assessment"))
        return cls(
            id=d["id"],
            name=d.get("name", ""),
            title=d.get("title", ""),
            status=d.get("status", "pending"),
            area=d.get("area", ""),
            priority=d.get("priority", "Media"),
            description=d.get("description", ""),
            problems_identified=d.get("problems_identified", []),
            acceptance=d.get("acceptance", []),
            files_to_touch=d.get("files_to_touch", d.get("files_touched", [])),
            risk_assessment=risk,
            completed_date=d.get("completed_date", d.get("completed_at", "")),
            started_in_session=d.get("started_in_session", d.get("session", "")),
            completed_in_session=d.get("completed_in_session", ""),
            dependencies=[str(x) for x in d.get("dependencies", [])],
            phase=d.get("phase", ""),
            fix=d.get("fix", []) if isinstance(d.get("fix"), list) else ([d["fix"]] if d.get("fix") else []),
            results=d.get("results"),
            completion_notes=d.get("completion_notes", d.get("summary", "")),
        )


@dataclass
class Session:
    id: int | None = None
    date: str = ""
    features_worked: list[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = ""

    @classmethod
    def from_row(cls, row: Any) -> Session:
        return cls(
            id=row["id"],
            date=row["date"],
            features_worked=json.loads(row["features_worked"] or "[]"),
            notes=row["notes"] or "",
            created_at=row["created_at"] or "",
        )


@dataclass
class AuditEntry:
    id: int | None = None
    feature_id: str = ""
    field_name: str = ""
    old_value: str = ""
    new_value: str = ""
    agent: str = ""
    timestamp: str = ""

    @classmethod
    def from_row(cls, row: Any) -> AuditEntry:
        return cls(
            id=row["id"],
            feature_id=row["feature_id"],
            field_name=row["field_name"],
            old_value=row["old_value"],
            new_value=row["new_value"],
            agent=row["agent"],
            timestamp=row["timestamp"],
        )


@dataclass
class Progress:
    id: int | None = None
    date: str = ""
    title: str = ""
    session_notes: str = ""
    features_worked: list[str] = field(default_factory=list)
    files_changed: list[str] = field(default_factory=list)
    verification: dict[str, Any] = field(default_factory=dict)
    content_md: str = ""
    is_current: bool = False
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row: Any) -> Progress:
        return cls(
            id=row["id"],
            date=row["date"],
            title=row["title"],
            session_notes=row["session_notes"] or "",
            features_worked=json.loads(row["features_worked"] or "[]"),
            files_changed=json.loads(row["files_changed"] or "[]"),
            verification=json.loads(row["verification"] or "{}"),
            content_md=row["content_md"] or "",
            is_current=bool(row["is_current"]),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )
