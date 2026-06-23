"""HTTP server for the harness web UI.

Usage:
    python -m harness.web.server [--port 8500]
"""

from __future__ import annotations

import json
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import mimetypes

WEB_DIR = Path(__file__).parent
DB_PATH = WEB_DIR.parent.parent / "harness.db"

# Ensure DB module is importable
sys.path.insert(0, str(WEB_DIR.parent.parent))


class HarnessHandler(BaseHTTPRequestHandler):
    """Serves the web UI and API endpoints."""

    db = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/features":
            self._json(self._api_features(params))
        elif path == "/api/stats":
            self._json(self._api_stats())
        elif path == "/api/health":
            self._json(self._api_health())
        elif path.startswith("/api/features/") and path.endswith("/audit"):
            fid = path.split("/")[3]
            self._json(self._api_audit(fid))
        elif path.startswith("/api/features/"):
            fid = path.split("/")[3]
            self._json(self._api_feature(fid))
        elif path == "/api/sessions":
            self._json(self._api_sessions())
        elif path == "/api/progress":
            self._json(self._api_progress(params))
        elif path == "/api/progress/current":
            self._json(self._api_progress_current())
        else:
            # Static files
            self._serve_file(path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        if path == "/api/features":
            self._json(self._api_create_feature(body))
        elif path.startswith("/api/features/") and path.endswith("/status"):
            fid = path.split("/")[3]
            self._json(self._api_update_status(fid, body))
        elif path.startswith("/api/features/") and path.endswith("/field"):
            fid = path.split("/")[3]
            self._json(self._api_update_field(fid, body))
        elif path.startswith("/api/features/") and path.endswith("/delete"):
            fid = path.split("/")[3]
            self._json(self._api_delete_feature(fid))
        elif path == "/api/migrate":
            self._json(self._api_migrate())
        elif path == "/api/export":
            self._json(self._api_export())
        elif path == "/api/progress/import":
            self._json(self._api_import_progress())
        else:
            self.send_error(404)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length > 0 else {}

        if path.startswith("/api/features/"):
            fid = path.split("/")[3]
            self._json(self._api_update_feature(fid, body))
        else:
            self.send_error(404)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── Static file serving ──────────────────────────────────────────

    def _serve_file(self, url_path: str) -> None:
        if url_path == "/":
            url_path = "/index.html"

        # Resolve to filesystem path within WEB_DIR
        file_path = WEB_DIR / url_path.lstrip("/")

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, f"Not found: {url_path}")
            return

        # Determine content type
        content_type, _ = mimetypes.guess_type(str(file_path))
        if content_type is None:
            content_type = "application/octet-stream"

        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    # ── JSON response helper ─────────────────────────────────────────

    def _json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── API: Features ────────────────────────────────────────────────

    def _api_features(self, params: dict) -> dict:
        status = params.get("status", [None])[0]
        area = params.get("area", [None])[0]
        features = self.db.list_features(status=status, area=area)
        return {"features": [f.to_dict() for f in features], "total": len(features)}

    def _api_feature(self, fid: str) -> dict:
        f = self.db.get_feature(fid)
        return {"feature": f.to_dict()} if f else {"error": f"Not found: {fid}"}

    def _api_stats(self) -> dict:
        counts = self.db.count_by_status()
        features = self.db.list_features()
        from collections import Counter

        areas = Counter(f.area for f in features if f.area)
        return {"counts": counts, "total": sum(counts.values()), "by_area": dict(areas.most_common())}

    def _api_health(self) -> dict:
        return self.db.health()

    def _api_audit(self, fid: str) -> dict:
        entries = self.db.get_audit_trail(fid)
        return {
            "entries": [
                {
                    "id": e.id,
                    "feature_id": e.feature_id,
                    "field_name": e.field_name,
                    "old_value": e.old_value,
                    "new_value": e.new_value,
                    "agent": e.agent,
                    "timestamp": e.timestamp,
                }
                for e in entries
            ]
        }

    def _api_sessions(self) -> dict:
        sessions = self.db.list_sessions()
        return {
            "sessions": [
                {"id": s.id, "date": s.date, "features_worked": s.features_worked, "notes": s.notes} for s in sessions
            ]
        }

    def _api_create_feature(self, body: dict) -> dict:
        from harness.models import Feature

        f = Feature(
            id=body["id"],
            name=body.get("name", ""),
            title=body.get("title", ""),
            status=body.get("status", "pending"),
            area=body.get("area", ""),
            priority=body.get("priority", "Media"),
            description=body.get("description", ""),
        )
        self.db.upsert_feature(f, agent=body.get("agent", "web"))
        return {"ok": True, "feature": f.to_dict()}

    def _api_update_status(self, fid: str, body: dict) -> dict:
        return {"ok": self.db.update_feature_field(fid, "status", body["status"], agent=body.get("agent", "web"))}

    def _api_update_field(self, fid: str, body: dict) -> dict:
        return {"ok": self.db.update_feature_field(fid, body["field"], body["value"], agent=body.get("agent", "web"))}

    def _api_update_feature(self, fid: str, body: dict) -> dict:
        for field, value in body.items():
            if field in (
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
            ):
                self.db.update_feature_field(fid, field, value, agent=body.get("agent", "web"))
        return {"ok": True}

    def _api_delete_feature(self, fid: str) -> dict:
        conn = self.db.connect()
        conn.execute("DELETE FROM features WHERE id = ?", (fid,))
        conn.commit()
        return {"ok": True}

    def _api_migrate(self) -> dict:
        from harness.migrate import migrate

        return migrate(db_path=self.db.db_path)

    def _api_export(self) -> dict:
        data = self.db.export_to_dict()
        output = self.db.db_path.parent / "feature_list_export.json"
        with open(output, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {"ok": True, "exported": len(data["features"]), "path": str(output)}

    # ── API: Progress ────────────────────────────────────────────────

    def _api_progress(self, params: dict) -> dict:
        limit = int(params.get("limit", [30])[0])
        entries = self.db.list_progress(limit=limit)
        return {
            "entries": [
                {
                    "id": p.id,
                    "date": p.date,
                    "title": p.title,
                    "session_notes": p.session_notes,
                    "features_worked": p.features_worked,
                    "files_changed": p.files_changed,
                    "verification": p.verification,
                    "is_current": p.is_current,
                }
                for p in entries
            ],
            "total": len(entries),
        }

    def _api_progress_current(self) -> dict:
        c = self.db.get_current_progress()
        if not c:
            return {"entry": None}
        return {
            "entry": {
                "id": c.id,
                "date": c.date,
                "title": c.title,
                "session_notes": c.session_notes,
                "features_worked": c.features_worked,
                "files_changed": c.files_changed,
                "verification": c.verification,
                "content_md": c.content_md[:3000],
            }
        }

    def _api_import_progress(self) -> dict:
        from harness.progress_parser import import_progress_from_md

        return import_progress_from_md(self.db)

    def log_message(self, fmt, *args):
        # Suppress log noise for API calls
        pass


def run_server(port: int = 8500) -> None:
    """Start the harness web server."""
    from harness.db import HarnessDB

    db = HarnessDB(DB_PATH)
    db.connect()
    HarnessHandler.db = db

    httpd = HTTPServer(("127.0.0.1", port), HarnessHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Harness web UI: {url}")
    print("Press Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        httpd.server_close()
        db.close()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8500
    run_server(port)
