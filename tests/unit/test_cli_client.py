"""Tests for the CLI API client module."""

from __future__ import annotations

from cli.client.http_client import (
    APIClient,
    ConfigData,
    HealthInfo,
    LogEntry,
    ModuleInfo,
    NetworkInfo,
    OutputInfo,
    PipelineStatus,
)


class TestPipelineStatus:
    def test_from_dict_full(self):
        data = {
            "state": "running",
            "mode": "thread_parallel",
            "chunks_processed": 42,
            "chunks_failed": 1,
            "avg_processing_time_ms": 1234.56,
            "uptime_seconds": 3600.0,
            "max_concurrent_chunks": 4,
            "concurrent_chunks": 2,
            "buffer_size": 10,
            "modules": [{"name": "transcriber", "state": "running"}],
            "system": {"cpu_percent": 45.0},
            "strategy": "thread_parallel",
        }
        s = PipelineStatus.from_dict(data)
        assert s.state == "running"
        assert s.chunks_processed == 42
        assert s.chunks_failed == 1
        assert s.avg_processing_time_ms == 1234.56
        assert s.modules == [{"name": "transcriber", "state": "running"}]
        assert s.system == {"cpu_percent": 45.0}

    def test_from_dict_empty(self):
        s = PipelineStatus.from_dict({})
        assert s.state == ""

    def test_fields_default_values(self):
        s = PipelineStatus()
        assert s.state == ""
        assert s.chunks_processed == 0
        assert not s.modules


class TestConfigData:
    def test_get_simple_key(self):
        c = ConfigData.from_dict({"server": {"port": 9999}})
        assert c.get("server.port") == 9999

    def test_get_nested(self):
        c = ConfigData.from_dict({"modules": {"transcriber": {"model": "tiny"}}})
        assert c.get("modules.transcriber.model") == "tiny"

    def test_get_missing(self):
        c = ConfigData.from_dict({})
        assert c.get("nonexistent.key") is None

    def test_set_value(self):
        c = ConfigData.from_dict({})
        c.set("server.port", 8080)
        assert c.raw["server"]["port"] == 8080

    def test_set_overwrite(self):
        c = ConfigData.from_dict({"server": {"port": 9999}})
        c.set("server.port", 8080)
        assert c.raw["server"]["port"] == 8080

    def test_set_creates_nested(self):
        c = ConfigData.from_dict({})
        c.set("a.b.c", 42)
        assert c.raw["a"]["b"]["c"] == 42


class TestLogEntry:
    def test_from_dict(self):
        entry = LogEntry.from_dict(
            {
                "level": "ERROR",
                "message": "test error",
                "timestamp": 1000000.0,
                "logger": "pipeline",
            }
        )
        assert entry.level == "ERROR"
        assert entry.message == "test error"
        assert entry.timestamp == 1000000.0

    def test_time_str(self):
        entry = LogEntry(timestamp=1000.0)
        assert len(entry.time_str) == 8  # HH:MM:SS format
        assert ":" in entry.time_str

    def test_time_str_zero(self):
        entry = LogEntry()
        assert entry.time_str == ""


class TestOutputInfo:
    def test_from_dict(self):
        o = OutputInfo.from_dict(
            {
                "name": "web_1",
                "type": "hls",
                "state": "running",
                "enabled": True,
                "processed_chunks": 10,
            }
        )
        assert o.name == "web_1"
        assert o.type == "hls"
        assert o.state == "running"

    def test_defaults(self):
        o = OutputInfo()
        assert o.name == ""
        assert o.state == "idle"


class TestModuleInfo:
    def test_from_dict(self):
        m = ModuleInfo.from_dict(
            {
                "name": "transcriber",
                "state": "running",
                "processed_chunks": 50,
            }
        )
        assert m.name == "transcriber"
        assert m.state == "running"

    def test_defaults(self):
        m = ModuleInfo()
        assert m.name == ""
        assert m.state == "idle"


class TestNetworkInfo:
    def test_from_dict(self):
        n = NetworkInfo.from_dict(
            {
                "server_ip": "192.168.1.1",
                "server_port": 9999,
                "stream_url": "srt://...",
            }
        )
        assert n.server_ip == "192.168.1.1"
        assert n.server_port == 9999

    def test_defaults(self):
        n = NetworkInfo()
        assert n.server_port == 9999


class TestHealthInfo:
    def test_from_dict(self):
        h = HealthInfo.from_dict(
            {
                "status": "ok",
                "uptime_seconds": 120.0,
                "pipeline_state": "running",
            }
        )
        assert h.status == "ok"
        assert h.pipeline_state == "running"


class TestAPIClientInit:
    def test_default_server(self):
        client = APIClient()
        assert client.base_url == "http://localhost:9999"
        assert client.token is None

    def test_custom_server(self):
        client = APIClient(base_url="http://10.0.0.1:8080", token="abc123")
        assert client.base_url == "http://10.0.0.1:8080"
        assert client.token == "abc123"

    def test_headers_with_token(self):
        client = APIClient(token="my-token")
        headers = client._headers()
        assert headers["Authorization"] == "Bearer my-token"
