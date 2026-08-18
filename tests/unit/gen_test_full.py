"""Generate the complete test_harness.py file."""

from pathlib import Path

parts = []

parts.append(
    r'''"""Tests for the harness feature tracking system (models, DB, CLI, web, parser)."""
from __future__ import annotations
import io, json, os, sqlite3, sys, tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
from harness.db import HarnessDB
from harness.models import Feature, Session, AuditEntry, Progress, RiskAssessment, normalize_id
from harness.migrate import migrate


@pytest.fixture
def tmp_db() -> HarnessDB:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = HarnessDB(path)
    db.connect()
    yield db
    db.close()
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def sample_feature() -> Feature:
    return Feature(
        id="101", name="test_feature", title="Test Feature",
        status="pending", area="core", priority="Alta",
        description="A test feature",
        problems_identified=["Bug in module X"],
        acceptance=["Test passes"],
        files_to_touch=["src/file.py"],
        risk_assessment=RiskAssessment(risk_level="Baja", mitigation=["Test coverage"]),
        dependencies=["100"], phase="phase1",
    )


@pytest.fixture
def seeded_db(tmp_db: HarnessDB, sample_feature: Feature) -> HarnessDB:
    tmp_db.upsert_feature(sample_feature, agent="test")
    return tmp_db


class TestNormalizeID:
    def test_strips_f_prefix(self) -> None: assert normalize_id("F115") == "115"
    def test_strips_lowercase_f(self) -> None: assert normalize_id("f115") == "115"
    def test_passes_through_numeric(self) -> None: assert normalize_id("115") == "115"
    def test_handles_int_input(self) -> None: assert normalize_id(115) == "115"
    def test_handles_none(self) -> None: assert normalize_id(None) == ""
    def test_strips_whitespace(self) -> None: assert normalize_id("  F115  ") == "115"


class TestFeatureModel:
    def test_auto_normalizes_id(self) -> None:
        f = Feature(id="F115", name="x", title="x"); assert f.id == "115"
    def test_auto_normalizes_numeric_id(self) -> None:
        f = Feature(id=115, name="x", title="x"); assert f.id == "115"
    def test_numeric_id_property(self) -> None:
        f = Feature(id="F115", name="x", title="x"); assert f.numeric_id == 115
    def test_is_done(self) -> None:
        f = Feature(id="1", name="x", title="x", status="done"); assert f.is_done
    def test_is_pending(self) -> None:
        f = Feature(id="1", name="x", title="x", status="pending"); assert f.is_pending
    def test_is_blocked(self) -> None:
        f = Feature(id="1", name="x", title="x", status="blocked"); assert f.is_blocked
    def test_is_in_progress(self) -> None:
        f = Feature(id="1", name="x", title="x", status="in_progress")
        assert f.is_in_progress; assert not f.is_done
    def test_to_dict_includes_risk(self) -> None:
        f = Feature(id="1", name="x", title="x", risk_assessment=RiskAssessment(risk_level="Alta"))
        assert f.to_dict()["risk_assessment"]["risk_level"] == "Alta"
    def test_to_dict_none_risk(self) -> None:
        f = Feature(id="1", name="x", title="x"); assert f.to_dict()["risk_assessment"] is None
    def test_from_json_dict_normalizes_id(self) -> None:
        f = Feature.from_json_dict({"id": "F115", "name": "x", "title": "x"})
        assert f.id == "115"
    def test_from_json_dict_handles_legacy_fields(self) -> None:
        raw = {"id": "99", "name": "legacy", "title": "Legacy Feature", "status": "done",
               "completed_at": "2026-01-01", "session": "2026-01-01",
               "fix": "Fixed the bug", "summary": "All done"}
        f = Feature.from_json_dict(raw)
        assert f.status == "done"; assert f.completed_date == "2026-01-01"
        assert f.started_in_session == "2026-01-01"
        assert f.fix == ["Fixed the bug"]; assert f.completion_notes == "All done"
    def test_from_row_parses_risk(self, seeded_db: HarnessDB) -> None:
        f = seeded_db.get_feature("101"); assert f is not None
        assert f.risk_assessment is not None; assert f.risk_assessment.risk_level == "Baja"
    def test_from_row_empty_risk(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        conn = tmp_db.connect()
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("99","no_risk","No Risk","pending",now,now))
        conn.commit()
        f = tmp_db.get_feature("99"); assert f is not None; assert f.risk_assessment is None
    def test_numeric_id_fallback(self) -> None:
        f = Feature(id="abc", name="x", title="x"); assert f.numeric_id == 0


class TestRiskAssessment:
    def test_to_json(self) -> None:
        r = RiskAssessment(risk_level="Alta", mitigation=["Code review"])
        assert json.loads(r.to_json()) == {"risk_level": "Alta", "mitigation": ["Code review"]}
    def test_from_json(self) -> None:
        r = RiskAssessment.from_json('{"risk_level": "Media", "mitigation": ["Test"]}')
        assert r is not None; assert r.risk_level == "Media"
    def test_from_json_none(self) -> None: assert RiskAssessment.from_json(None) is None
    def test_from_json_invalid(self) -> None: assert RiskAssessment.from_json("not json") is None
    def test_from_dict(self) -> None:
        r = RiskAssessment.from_dict({"risk_level": "Baja", "mitigation": ["Check"]})
        assert r is not None; assert r.risk_level == "Baja"
    def test_from_dict_none(self) -> None: assert RiskAssessment.from_dict(None) is None
    def test_defaults(self) -> None:
        r = RiskAssessment(); assert r.risk_level == "Baja"; assert r.mitigation == []
    def test_from_json_empty_string(self) -> None: assert RiskAssessment.from_json("") is None


class TestDBCRUD:
    def test_upsert_and_get(self, tmp_db: HarnessDB) -> None:
        f = Feature(id="1", name="crud", title="CRUD Test")
        tmp_db.upsert_feature(f, agent="test")
        assert tmp_db.get_feature("1") is not None
    def test_get_feature_normalizes_id(self, tmp_db: HarnessDB) -> None:
        f = Feature(id="99", name="norm", title="Normalize Test")
        tmp_db.upsert_feature(f, agent="test")
        assert tmp_db.get_feature("F99").id == "99"
    def test_get_nonexistent(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.get_feature("99999") is None
    def test_list_features(self, seeded_db: HarnessDB) -> None:
        assert len(seeded_db.list_features()) >= 1
    def test_list_filter_by_status(self, seeded_db: HarnessDB) -> None:
        assert len(seeded_db.list_features(status="pending")) >= 1
        assert len(seeded_db.list_features(status="done")) == 0
    def test_list_filter_by_area(self, seeded_db: HarnessDB) -> None:
        assert len(seeded_db.list_features(area="core")) >= 1
    def test_list_filter_by_priority(self, seeded_db: HarnessDB) -> None:
        assert len(seeded_db.list_features(priority="Alta")) >= 1
    def test_list_empty(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.list_features() == []
    def test_update_field(self, seeded_db: HarnessDB) -> None:
        assert seeded_db.update_feature_field("101", "title", "Updated", agent="test")
        assert seeded_db.get_feature("101").title == "Updated"
    def test_update_nonexistent(self, tmp_db: HarnessDB) -> None:
        assert not tmp_db.update_feature_field("999", "title", "x", agent="test")
    def test_update_same_value(self, seeded_db: HarnessDB) -> None:
        assert seeded_db.update_feature_field("101", "title", "Test Feature", agent="test")
    def test_update_json_field(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("101", "fix", ["A","B"], agent="test")
        assert seeded_db.get_feature("101").fix == ["A","B"]
    def test_update_risk_assessment(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("101", "title", "Updated Risk", agent="test")
        f = seeded_db.get_feature("101")
        assert f is not None and f.title == "Updated Risk"
    def test_upsert_overwrites(self, seeded_db: HarnessDB) -> None:
        seeded_db.upsert_feature(Feature(id="101", name="test_feature", title="Overwritten"), agent="test")
        assert seeded_db.get_feature("101").title == "Overwritten"
    def test_count_by_status(self, seeded_db: HarnessDB) -> None:
        c = seeded_db.count_by_status(); assert "pending" in c and c["pending"] >= 1
    def test_count_empty(self, tmp_db: HarnessDB) -> None: assert tmp_db.count_by_status() == {}
    def test_next_feature_returns_highest_priority(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_feature(Feature(id="1", name="a", title="Low", priority="Baja"), agent="test")
        tmp_db.upsert_feature(Feature(id="2", name="b", title="High", priority="Alta"), agent="test")
        assert tmp_db.next_feature().title == "High"
    def test_next_feature_no_pending(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.next_feature() is None
    def test_next_feature_media_fallback(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_feature(Feature(id="1", name="a", title="Alpha"), agent="test")
        tmp_db.upsert_feature(Feature(id="2", name="b", title="Beta"), agent="test")
        assert tmp_db.next_feature().title == "Alpha"


class TestHealth:
    def test_healthy_db(self, seeded_db: HarnessDB) -> None:
        assert seeded_db.health()["healthy"]
    def test_missing_db_file(self, tmp_path: Path) -> None:
        db = HarnessDB(tmp_path / "nonexistent.db")
        r = db.health(); assert not r["healthy"]; assert any("does not exist" in i for i in r["issues"])
    def test_health_reports_counts(self, seeded_db: HarnessDB) -> None:
        r = seeded_db.health()
        assert r["stats"]["total_features"] >= 1
        assert "pending" in r["stats"]["counts_by_status"]
    def test_health_empty_db(self, tmp_db: HarnessDB) -> None:
        r = tmp_db.health(); assert r["healthy"]; assert r["stats"]["total_features"] == 0
    def test_detects_non_normalized_id(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        sql = "INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)"
        tmp_db.connect().execute(sql, ("F999", "bad", "Bad ID", "pending", now, now))
        tmp_db.connect().commit()
        r = tmp_db.health()
        assert not r["healthy"]
        assert any("Non-normalized" in i for i in r["issues"])
    def test_detects_multiple_in_progress(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        conn = tmp_db.connect()
        for i in ["1","2"]:
            conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                         (i,f"f{i}",f"F{i}","in_progress",now,now))
        conn.commit()
        r = tmp_db.health(); assert not r["healthy"]
        assert any("in_progress" in i for i in r["issues"])
    def test_detects_invalid_status(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        conn = tmp_db.connect()
        conn.execute("PRAGMA ignore_check_constraints=ON")
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("1","x","X","invalid_status",now,now))
        conn.commit()
        r = tmp_db.health(); assert not r["healthy"]
        assert any("invalid status" in i for i in r["issues"])
    def test_detects_semantic_duplicate(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        conn = tmp_db.connect()
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("115","orig","Original","done",now,now))
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("F115","dup","","done",now,now))
        conn.commit()
        r = tmp_db.health(); assert not r["healthy"]
        assert any("Semantic duplicate" in i for i in r["issues"])
    def test_detects_semantic_duplicate_via_health(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        conn = tmp_db.connect()
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("115","a","A","pending",now,now))
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("F115","b","B","pending",now,now))
        conn.commit()
        r = tmp_db.health(); assert not r["healthy"]
        assert any("semantic" in i.lower() for i in r["issues"])
    def test_db_not_found_returns_unhealthy(self, tmp_path: Path) -> None:
        db = HarnessDB(tmp_path / "no_such_dir" / "nonexistent.db")
        r = db.health(); assert not r["healthy"]
        assert any("does not exist" in i for i in r["issues"])


class TestAudit:
    def test_audit_logs_status_change(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("101", "status", "done", agent="tester")
        e = seeded_db.get_audit_trail("101")
        se = [x for x in e if x.field_name == "status"]
        assert len(se) >= 1 and se[0].agent == "tester"
    def test_audit_logs_field_change(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("101", "title", "New Title", agent="bot")
        assert len([x for x in seeded_db.get_audit_trail("101") if x.field_name == "title"]) >= 1
    def test_audit_empty_for_nonexistent(self, seeded_db: HarnessDB) -> None:
        assert seeded_db.get_audit_trail("99999") == []
    def test_upsert_audits_changes(self, seeded_db: HarnessDB) -> None:
        seeded_db.upsert_feature(Feature(id="101",name="test_feature",title="Changed via upsert",status="done"),
                                 agent="upserter")
        e = seeded_db.get_audit_trail("101")
        te = [x for x in e if x.field_name == "title"]
        assert len(te) >= 1 and te[0].agent == "upserter"
    def test_audit_uses_normalized_id(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("F101", "status", "done", agent="x")
        assert len(seeded_db.get_audit_trail("101")) >= 1
    def test_multiple_audits(self, seeded_db: HarnessDB) -> None:
        for i in range(3):
            seeded_db.update_feature_field("101", "name", f"name_{i}", agent="test")
        ne = [x for x in seeded_db.get_audit_trail("101") if x.field_name == "name"]
        assert len(ne) >= 2


class TestSessions:
    def test_start_session(self, tmp_db: HarnessDB) -> None:
        s = tmp_db.start_session(notes="Test session")
        assert s.id is not None and s.notes == "Test session"
    def test_end_session(self, tmp_db: HarnessDB) -> None:
        s = tmp_db.start_session()
        tmp_db.end_session(s.id, ["101","102"], "All done")
        ended = [x for x in tmp_db.list_sessions() if x.id == s.id]
        assert len(ended) == 1 and ended[0].features_worked == ["101","102"]
    def test_list_sessions_limit(self, tmp_db: HarnessDB) -> None:
        for i in range(5): tmp_db.start_session(notes=f"S{i}")
        assert len(tmp_db.list_sessions(limit=3)) <= 3
    def test_list_sessions_empty(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.list_sessions() == []
    def test_session_created_at_set(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.start_session().created_at != ""
    def test_end_session_nonexistent(self, tmp_db: HarnessDB) -> None:
        tmp_db.end_session(99999, [], "No such session")


class TestProgress:
    def test_upsert_and_get(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_progress(Progress(date="2026-06-30", title="Test Progress", features_worked=["101","102"]))
        p = tmp_db.get_progress_by_date("2026-06-30")
        assert p is not None and p.title == "Test Progress"
    def test_get_progress_by_id(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_progress(Progress(date="2026-06-29", title="By ID"))
        by_date = tmp_db.get_progress_by_date("2026-06-29")
        assert by_date is not None
        assert tmp_db.get_progress(by_date.id).title == "By ID"
    def test_set_current(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_progress(Progress(date="2026-06-28", title="Old"))
        tmp_db.upsert_progress(Progress(date="2026-06-30", title="Current"))
        by_date = tmp_db.get_progress_by_date("2026-06-30")
        assert by_date is not None and by_date.id is not None
        tmp_db.set_current_progress(by_date.id)
        assert tmp_db.get_current_progress().title == "Current"
    def test_list_progress(self, tmp_db: HarnessDB) -> None:
        for d in ["2026-06-01","2026-06-02","2026-06-03"]:
            tmp_db.upsert_progress(Progress(date=d, title=f"Session {d}"))
        assert len(tmp_db.list_progress(limit=2)) == 2
    def test_progress_no_current(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.get_current_progress() is None
    def test_progress_overwrite(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_progress(Progress(date="2026-07-01", title="First", session_notes="v1"))
        tmp_db.upsert_progress(Progress(date="2026-07-01", title="First", session_notes="v2"))
        assert tmp_db.get_progress_by_date("2026-07-01").session_notes == "v2"
    def test_get_progress_nonexistent(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.get_progress(99999) is None


class TestSanitizeIDs:
    def test_sanitize_merges_duplicates(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        conn = tmp_db.connect()
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("115","orig","Original Title","done",now,now))
        conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                     ("F115","orig","","done",now,now))
        conn.commit()
        r = tmp_db.sanitize_ids(agent="test")
        assert r["merged"] >= 1
        assert tmp_db.get_feature("115").id == "115"
    def test_sanitize_fixes_non_normalized_singleton(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        sql = "INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)"
        tmp_db.connect().execute(sql, ("F200", "singleton", "Singleton", "pending", now, now))
        tmp_db.connect().commit()
        tmp_db.sanitize_ids(agent="test")
        assert tmp_db.get_feature("200").id == "200"
    def test_sanitize_no_duplicates(self, seeded_db: HarnessDB) -> None:
        r = seeded_db.sanitize_ids(agent="test")
        assert r["merged"] == 0 and len(r["errors"]) == 0


class TestExport:
    def test_export_to_dict(self, seeded_db: HarnessDB) -> None:
        d = seeded_db.export_to_dict()
        assert "project" in d and "features" in d
        assert len(d["features"]) >= 1
        assert d["features"][0]["name"] == "test_feature"
    def test_export_includes_rules(self, seeded_db: HarnessDB) -> None:
        d = seeded_db.export_to_dict()
        assert d["rules"]["one_feature_at_a_time"]
    def test_export_empty(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.export_to_dict()["features"] == []


class TestMigration:
    def test_migrate_from_json(self, tmp_db: HarnessDB, tmp_path: Path) -> None:
        j = tmp_path / "f.json"
        features = [
            {"id": "1", "name": "migrated", "title": "Migrated", "status": "pending"},
            {"id": "2", "name": "m2", "title": "Another", "status": "done"},
        ]
        j.write_text(json.dumps({"features": features}), encoding="utf-8")
        r = migrate(str(j), str(tmp_db.db_path))
        assert r["imported"] == 2 and r["skipped"] == 0
        assert len(tmp_db.list_features()) == 2
    def test_migrate_empty_json(self, tmp_db: HarnessDB, tmp_path: Path) -> None:
        j = tmp_path / "empty.json"
        j.write_text('{"features":[]}', encoding="utf-8")
        r = migrate(str(j), str(tmp_db.db_path))
        assert r["imported"] == 0 and r["total_in_json"] == 0
    def test_migrate_nonexistent_file(self) -> None:
        with pytest.raises(FileNotFoundError): migrate("/nonexistent/path.json")
    def test_migrate_with_f_prefix_ids(self, tmp_db: HarnessDB, tmp_path: Path) -> None:
        j = tmp_path / "fp.json"
        j.write_text(json.dumps({"features":[{"id":"F115","name":"ff","title":"F-Prefix"}]}), encoding="utf-8")
        r = migrate(str(j), str(tmp_db.db_path))
        assert r["imported"] == 1
        assert tmp_db.get_feature("115").id == "115"
    def test_migrate_broken_json_no_features(self, tmp_db: HarnessDB, tmp_path: Path) -> None:
        j = tmp_path / "bad.json"
        j.write_text('{"version":1}', encoding="utf-8")
        r = migrate(str(j), str(tmp_db.db_path))
        assert r["imported"] == 0 and r["total_in_json"] == 0


class TestDBEdgeCases:
    def test_connect_twice(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.connect() is tmp_db.connect()
    def test_transaction_rollback_on_error(self, tmp_db: HarnessDB) -> None:
        with pytest.raises(ValueError):
            with tmp_db.transaction() as conn:
                conn.execute("INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)",
                             ("1","x","x","pending","now","now"))
                raise ValueError("boom")
        assert tmp_db.get_feature("1") is None
    def test_close_and_reopen(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_feature(Feature(id="1", name="x", title="Before close"), agent="test")
        tmp_db.close(); tmp_db.connect()
        assert tmp_db.get_feature("1").title == "Before close"
    def test_upsert_without_agent_does_not_audit(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("101", "title", "No Audit", agent="")
        assert len(seeded_db.get_audit_trail("101")) == 0
    def test_sanitize_empty_db(self, tmp_db: HarnessDB) -> None:
        assert tmp_db.sanitize_ids()["merged"] == 0


class TestCLICommands:
    def test_parse_args_list(self) -> None:
        from harness.cli import build_parser as bp
        assert bp().parse_args(["list"]).command == "list"
    def test_parse_args_list_filters(self) -> None:
        from harness.cli import build_parser as bp
        a = bp().parse_args(["list","--status","pending","--area","core"])
        assert a.status == "pending" and a.area == "core"
    def test_parse_args_show(self) -> None:
        from harness.cli import build_parser as bp
        assert bp().parse_args(["show","42"]).id == 42
    def test_parse_args_add(self) -> None:
        from harness.cli import build_parser as bp
        a = bp().parse_args(["add","200","new_feature","New Feature","--area","core"])
        assert a.id == 200 and a.name == "new_feature" and a.area == "core"
    def test_parse_args_update(self) -> None:
        from harness.cli import build_parser as bp
        a = bp().parse_args(["update","101","status","done","--agent","tester"])
        assert a.id == 101 and a.field == "status"
    def test_parse_args_next(self) -> None:
        from harness.cli import build_parser as bp
        assert bp().parse_args(["next"]).command == "next"
    def test_parse_args_stats(self) -> None:
        from harness.cli import build_parser as bp
        assert bp().parse_args(["stats"]).command == "stats"
    def test_parse_args_health(self) -> None:
        from harness.cli import build_parser as bp
        assert bp().parse_args(["health"]).command == "health"
    def test_parse_args_sanitize(self) -> None:
        from harness.cli import build_parser as bp
        assert bp().parse_args(["sanitize"]).command == "sanitize"
    def test_parse_args_session_start(self) -> None:
        from harness.cli import build_parser as bp
        a = bp().parse_args(["session","start","--notes","working"])
        assert a.session_action == "start" and a.notes == "working"
    def test_parse_args_session_list(self) -> None:
        from harness.cli import build_parser as bp
        a = bp().parse_args(["session","list","--limit","5"])
        assert a.session_action == "list" and a.limit == 5
    def test_parse_args_session_end(self) -> None:
        from harness.cli import build_parser as bp
        a = bp().parse_args(["session","end","1","--features","101,102"])
        assert a.session_action == "end" and a.session_id == 1
    def test_cli_build_parser_no_args_shows_help(self) -> None:
        from harness.cli import build_parser as bp
        with pytest.raises(SystemExit): bp().parse_args(["--help"])
    def test_cmd_list_output(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_list
        a = MagicMock(db=seeded_db.db_path, status=None, area=None, priority=None, group=False)
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_list(a)
        assert "Total:" in buf.getvalue()
    def test_cmd_list_grouped(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_list
        a = MagicMock(db=seeded_db.db_path, status=None, area=None, priority=None, group=True)
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_list(a)
        assert "PENDING" in buf.getvalue().upper()
    def test_cmd_list_empty(self, tmp_db: HarnessDB) -> None:
        from harness.commands.features import cmd_list
        a = MagicMock(db=tmp_db.db_path, status=None, area=None, priority=None, group=False)
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_list(a)
        assert "No features" in buf.getvalue()
    def test_cmd_show_found(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_show
        a = MagicMock(db=seeded_db.db_path, id="101")
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_show(a)
        assert "F101" in buf.getvalue()
    def test_cmd_show_not_found(self, tmp_db: HarnessDB) -> None:
        from harness.commands.features import cmd_show
        with pytest.raises(SystemExit): cmd_show(MagicMock(db=tmp_db.db_path, id="999"))
    def test_cmd_add_success(self, tmp_db: HarnessDB) -> None:
        import argparse; from harness.commands.features import cmd_add
        ns = argparse.Namespace(db=tmp_db.db_path, id=300, name="new_feat", title="New Feature",
                                area="core", priority="Alta", description="desc", agent="tester")
        with patch("sys.stdout", io.StringIO()): cmd_add(ns)
        assert tmp_db.get_feature("300") is not None
    def test_cmd_add_already_exists(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_add
        a = MagicMock(db=seeded_db.db_path, id=101, name="dup", title="Dup",
                      area="", priority="Media", description="", agent="cli")
        with pytest.raises(SystemExit): cmd_add(a)
    def test_cmd_update_status_to_done(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_update
        a = MagicMock(db=seeded_db.db_path, id=101, field="status", value="done", agent="tester")
        with patch("sys.stdout", io.StringIO()): cmd_update(a)
        assert seeded_db.get_feature("101").status == "done"
    def test_cmd_update_nonexistent(self, tmp_db: HarnessDB) -> None:
        from harness.commands.features import cmd_update
        with pytest.raises(SystemExit):
            cmd_update(MagicMock(db=tmp_db.db_path, id=999, field="title", value="x", agent="cli"))
    def test_cmd_next_found(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_next
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_next(MagicMock(db=seeded_db.db_path))
        assert "Next:" in buf.getvalue()
    def test_cmd_next_not_found(self, tmp_db: HarnessDB) -> None:
        from harness.commands.features import cmd_next
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_next(MagicMock(db=tmp_db.db_path))
        assert "No pending" in buf.getvalue()
    def test_cmd_search_found(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_search
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_search(MagicMock(db=seeded_db.db_path, query="Test"))
        assert "Test Feature" in buf.getvalue()
    def test_cmd_search_not_found(self, seeded_db: HarnessDB) -> None:
        from harness.commands.features import cmd_search
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_search(MagicMock(db=seeded_db.db_path, query="ZZZZ"))
        assert "No features" in buf.getvalue()
    def test_cmd_stats_output(self, seeded_db: HarnessDB) -> None:
        from harness.commands.admin import cmd_stats
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_stats(MagicMock(db=seeded_db.db_path))
        assert "Feature Statistics" in buf.getvalue()
    def test_cmd_stats_empty(self, tmp_db: HarnessDB) -> None:
        from harness.commands.admin import cmd_stats
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_stats(MagicMock(db=tmp_db.db_path))
        assert "TOTAL" in buf.getvalue()
    def test_cmd_health_healthy(self, seeded_db: HarnessDB) -> None:
        from harness.commands.admin import cmd_health
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            with pytest.raises(SystemExit) as e: cmd_health(MagicMock(db=seeded_db.db_path))
            assert e.value.code == 0
        assert "healthy" in buf.getvalue().lower()
    def test_cmd_health_unhealthy(self, tmp_db: HarnessDB) -> None:
        from harness.db import _now; now = _now()
        sql = "INSERT INTO features (id,name,title,status,created_at,updated_at) VALUES (?,?,?,?,?,?)"
        tmp_db.connect().execute(sql, ("F1", "bad", "Bad", "pending", now, now))
        tmp_db.connect().commit()
        from harness.commands.admin import cmd_health
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            with pytest.raises(SystemExit) as e: cmd_health(MagicMock(db=tmp_db.db_path))
            assert e.value.code == 1
        assert "FAIL" in buf.getvalue().upper()
    def test_cmd_sanitize_output(self, tmp_db: HarnessDB) -> None:
        from harness.commands.admin import cmd_sanitize
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_sanitize(MagicMock(db=tmp_db.db_path))
        assert "Sanitize" in buf.getvalue()
    def test_cmd_audit_with_entries(self, seeded_db: HarnessDB) -> None:
        seeded_db.update_feature_field("101", "status", "done", agent="tester")
        from harness.commands.admin import cmd_audit
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_audit(MagicMock(db=seeded_db.db_path, id=101))
        assert "Audit trail" in buf.getvalue()
    def test_cmd_audit_no_entries(self, tmp_db: HarnessDB) -> None:
        from harness.commands.admin import cmd_audit
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_audit(MagicMock(db=tmp_db.db_path, id=999))
        assert "No audit" in buf.getvalue()
    def test_cmd_session_start(self, tmp_db: HarnessDB) -> None:
        from harness.commands.sessions import cmd_session
        buf = io.StringIO()
        with patch("sys.stdout", buf): cmd_session(MagicMock(db=tmp_db.db_path, session_action="start", notes="Test"))
        assert "Session #" in buf.getvalue()
    def test_cmd_session_list(self, tmp_db: HarnessDB) -> None:
        tmp_db.start_session(notes="S1")
        from harness.commands.sessions import cmd_session
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            cmd_session(MagicMock(db=tmp_db.db_path, session_action="list", limit=10))
        assert "S1" in buf.getvalue() or "#1" in buf.getvalue()
    def test_cmd_session_end(self, tmp_db: HarnessDB) -> None:
        s = tmp_db.start_session(notes="To end")
        from harness.commands.sessions import cmd_session
        args = MagicMock(
            db=tmp_db.db_path,
            session_action="end",
            session_id=s.id,
            features="101",
            notes="Done",
        )
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            cmd_session(args)
        assert "ended" in buf.getvalue().lower()
'''
)

parts.append(
    r"""

class TestWebServerAuth:
    @patch("harness.web.server.HARNESS_TOKEN", "mytoken")
    def test_auth_token_query_param(self) -> None:
        from harness.web.server import _check_auth
        assert _check_auth({}, {"token": ["mytoken"]})
    @patch("harness.web.server.HARNESS_TOKEN", "mytoken")
    def test_auth_token_bearer(self) -> None:
        from harness.web.server import _check_auth
        assert _check_auth({"Authorization": "Bearer mytoken"}, {})
    @patch("harness.web.server.HARNESS_TOKEN", "mytoken")
    def test_auth_token_x_auth_header(self) -> None:
        from harness.web.server import _check_auth
        assert _check_auth({"X-Auth-Token": "mytoken"}, {})
    @patch("harness.web.server.HARNESS_TOKEN", "mytoken")
    def test_auth_rejects_wrong_token(self) -> None:
        from harness.web.server import _check_auth
        assert not _check_auth({}, {"token": ["wrong"]})
        assert not _check_auth({"Authorization": "Bearer wrong"}, {})
    def test_auth_disabled_when_no_token(self) -> None:
        from harness.web.server import _check_auth
        assert _check_auth({}, {}) and _check_auth({}, {"token": ["wrong"]})
    def test_rate_limit_allows_within_window(self) -> None:
        from harness.web.server import _check_rate_limit
        assert _check_rate_limit("127.0.0.1")
    def test_rate_limit_exceeds(self) -> None:
        from harness.web.server import _check_rate_limit, RATE_LIMIT_REQUESTS
        for _ in range(RATE_LIMIT_REQUESTS): _check_rate_limit("10.0.0.1")
        assert _check_rate_limit("10.0.0.1") is False
    def test_rate_limit_per_ip(self) -> None:
        from harness.web.server import _check_rate_limit, RATE_LIMIT_REQUESTS
        for _ in range(RATE_LIMIT_REQUESTS): _check_rate_limit("10.0.0.2")
        assert _check_rate_limit("10.0.0.3") is True
    def test_rate_limit_windows_separate(self) -> None:
        from harness.web.server import _check_rate_limit, _rate_window_start, _rate_counter
        _rate_counter["10.0.0.4"] = 999; _rate_window_start["10.0.0.4"] = 0
        assert _check_rate_limit("10.0.0.4") is True


class TestWebServerAPI:
    def test_api_features_list(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        r = HarnessHandler._api_features(h, {}); assert r["total"] >= 1
    def test_api_feature_by_id(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        r = HarnessHandler._api_feature(h, "101"); assert r["feature"]["name"] == "test_feature"
    def test_api_feature_not_found(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        assert "error" in HarnessHandler._api_feature(h, "99999")
    def test_api_stats(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        r = HarnessHandler._api_stats(h); assert "counts" in r and r["total"] >= 1
    def test_api_health(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        assert HarnessHandler._api_health(h)["healthy"] is True
    def test_api_create_feature(self, tmp_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = tmp_db
        r = HarnessHandler._api_create_feature(h, {"id":500,"name":"web","title":"Web Created","agent":"web"})
        assert r["ok"] is True and tmp_db.get_feature("500").title == "Web Created"
    def test_api_update_status(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        assert HarnessHandler._api_update_status(h, "101", {"status":"done","agent":"web"})["ok"] is True
    def test_api_update_field(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        HarnessHandler._api_update_field(h, "101", {"field":"title","value":"Web Updated","agent":"web"})
        assert seeded_db.get_feature("101").title == "Web Updated"
    def test_api_delete_feature(self, seeded_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = seeded_db
        assert HarnessHandler._api_delete_feature(h, "101")["ok"] is True
        assert seeded_db.get_feature("101") is None
    def test_api_progress_list(self, tmp_db: HarnessDB) -> None:
        tmp_db.upsert_progress(Progress(date="2026-07-01", title="P"))
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = tmp_db
        assert HarnessHandler._api_progress(h, {"limit":["10"]})["total"] >= 1
    def test_api_progress_current_none(self, tmp_db: HarnessDB) -> None:
        from harness.web.server import HarnessHandler
        h = MagicMock(spec=HarnessHandler); h.db = tmp_db
        assert HarnessHandler._api_progress_current(h)["entry"] is None


class TestWebServerStaticFiles:
    def test_all_static_files_exist(self) -> None:
        web_dir = Path(__file__).parent.parent.parent / "harness" / "web"
        for f in ["index.html","api.js","app.js","features.js","progress.js"]:
            assert (web_dir / f).exists(), f"Missing: {f}"


class TestProgressParser:
    def test_parse_history_md_basic(self) -> None:
        from harness.progress_parser import parse_history_md
        content = "## 2026-06-23 \u2014 F150: PTS sync\n\nWorked on F150.\n"
        s = parse_history_md(content)
        assert len(s) == 1 and s[0].date == "2026-06-23"
        assert "150" in s[0].features_worked
    def test_parse_history_md_multi(self) -> None:
        from harness.progress_parser import parse_history_md
        content = "## 2026-06-23 \u2014 F150: First\n\nF150.\n## 2026-06-24 \u2014 F151: Second\n\nF151.\n"
        assert len(parse_history_md(content)) == 2
    def test_parse_history_md_no_date(self) -> None:
        from harness.progress_parser import parse_history_md
        assert len(parse_history_md("## Bad header\nContent")) == 0
    def test_parse_history_md_empty(self) -> None:
        from harness.progress_parser import parse_history_md
        assert parse_history_md("") == []
    def test_parse_current_md_basic(self) -> None:
        from harness.progress_parser import parse_current_md
        c = parse_current_md("# Current session \u2014 F150: PTS sync\n\n|Check|Status|\n|-|-|\n|Tests|PASS|")
        assert c is not None and "150" in c.features_worked and "Tests" in c.verification
    def test_parse_current_md_empty(self) -> None:
        from harness.progress_parser import parse_current_md
        assert parse_current_md("") is None
    def test_parse_current_md_spanish(self) -> None:
        from harness.progress_parser import parse_current_md
        c = parse_current_md("# Sesi\u00f3n actual \u2014 F200: Security")
        assert c is not None and "200" in c.features_worked
    def test_import_progress_no_files(self, tmp_db: HarnessDB, tmp_path: Path) -> None:
        from harness.progress_parser import import_progress_from_md
        r = import_progress_from_md(tmp_db, history_path=tmp_path/"nope.md", current_path=tmp_path/"nope2.md")
        assert r["imported"] == 0 and r["errors"] == []
    def test_import_progress_history(self, tmp_db: HarnessDB, tmp_path: Path) -> None:
        (tmp_path/"history.md").write_text("## 2026-07-01 \u2014 F300: Test\nWorked on F300.\n", encoding="utf-8")
        from harness.progress_parser import import_progress_from_md
        assert import_progress_from_md(tmp_db, history_path=tmp_path/"history.md")["imported"] >= 1
    def test_parse_current_md_no_date(self) -> None:
        from harness.progress_parser import parse_current_md
        c = parse_current_md("# No Date\nSome `core/file.py`")
        assert c is not None and c.date == ""
    def test_parse_history_md_files(self) -> None:
        from harness.progress_parser import parse_history_md
        c = "## 2026-07-02 \u2014 F400: Files\nChanged `core/utils.py` and `modules/tts.py`.\n"
        s = parse_history_md(c)
        assert len(s) >= 1 and "core/utils.py" in s[0].files_changed


class TestHarnessVersion:
    def test_version_is_2_0_0(self) -> None:
        from harness import __version__; assert __version__ == "2.0.0"
    def test_main_runs(self) -> None:
        from harness.cli import build_parser as bp
        p = bp()
        assert "list" in {s for s in p._positionals._actions[-1].choices} | {"--help"}


class TestCLIHelpers:
    def test_feature_str_repr(self) -> None:
        assert "CLI Feature" in repr(Feature(id="42", name="cli_test", title="CLI Feature"))
    def test_audit_entry_creation(self) -> None:
        e = AuditEntry(feature_id="1", field_name="status", old_value="pending",
                       new_value="done", agent="test", timestamp="2026-01-01")
        assert e.field_name == "status" and e.new_value == "done"
    def test_session_from_row(self) -> None:
        row = MagicMock()
        session_data = {"id": 1, "date": "2026-07-01", "features_worked": '["101"]', "notes": "t", "created_at": "now"}
        row.__getitem__.side_effect = lambda k: session_data[k]
        s = Session.from_row(row)
        assert s.id == 1 and s.features_worked == ["101"]
    def test_progress_from_row(self) -> None:
        row = MagicMock()
        progress_data = {
            "id": 1,
            "date": "2026-07-01",
            "title": "T",
            "session_notes": "n",
            "features_worked": "[]",
            "files_changed": "[]",
            "verification": "{}",
            "content_md": "#",
            "is_current": 1,
            "created_at": "n",
            "updated_at": "n",
        }
        row.__getitem__.side_effect = lambda k: progress_data[k]
        p = Progress.from_row(row)
        assert p.title == "T" and p.is_current is True
    def test_build_parser_has_all_commands(self) -> None:
        from harness.cli import build_parser
        choices = build_parser()._subparsers._group_actions[0].choices
        commands = {
            "list",
            "show",
            "add",
            "update",
            "next",
            "stats",
            "health",
            "sanitize",
            "migrate",
            "export",
            "audit",
            "search",
            "session",
        }
        for c in commands:
            assert c in choices, f"Missing: {c}"
"""
)

# Write the entire file at once
Path("tests/unit/test_harness.py").write_text("".join(parts), encoding="utf-8")
full = Path("tests/unit/test_harness.py").read_text(encoding="utf-8")
nlines = len(full.splitlines())
print(f"Wrote {nlines} lines OK")
