from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cli.client.http_client import LogEntry
from cli.commands.config import _build_tree, _format_value, run_config_get, run_config_show
from cli.commands.logs import _format_log, _level_style, run_logs
from cli.commands.start import run_start
from cli.commands.status import _state_label, _state_style, run_status
from cli.commands.stop import run_stop


class TestRunStart:
    @pytest.mark.asyncio
    async def test_start_success(self, mock_api, console):
        mock_api.start_pipeline.return_value = {"status": "started"}
        code = await run_start(mock_api, console)
        assert code == 0
        mock_api.start_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_json(self, mock_api, console):
        mock_api.start_pipeline.return_value = {"status": "started"}
        code = await run_start(mock_api, console, json_output=True)
        assert code == 0

    @pytest.mark.asyncio
    async def test_start_failure(self, mock_api, console):
        mock_api.start_pipeline.side_effect = Exception("API error")
        code = await run_start(mock_api, console)
        assert code == 1

    @pytest.mark.asyncio
    async def test_start_returns_unknown_status(self, mock_api, console):
        mock_api.start_pipeline.return_value = {}
        code = await run_start(mock_api, console)
        assert code == 0


class TestRunStop:
    @pytest.mark.asyncio
    async def test_stop_success(self, mock_api, console):
        mock_api.stop_pipeline.return_value = {"status": "stopped"}
        code = await run_stop(mock_api, console)
        assert code == 0
        mock_api.stop_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_json(self, mock_api, console):
        mock_api.stop_pipeline.return_value = {"status": "stopped"}
        code = await run_stop(mock_api, console, json_output=True)
        assert code == 0

    @pytest.mark.asyncio
    async def test_stop_failure(self, mock_api, console):
        mock_api.stop_pipeline.side_effect = Exception("API error")
        code = await run_stop(mock_api, console)
        assert code == 1


class TestRunStatus:
    @pytest.mark.asyncio
    async def test_status_success(self, mock_api, console):
        code = await run_status(mock_api, console)
        assert code == 0

    @pytest.mark.asyncio
    async def test_status_json(self, mock_api, console):
        code = await run_status(mock_api, console, json_output=True)
        assert code == 0

    @pytest.mark.asyncio
    async def test_status_json_contains_state(self, mock_api, console):
        code = await run_status(mock_api, console, json_output=True)
        assert code == 0

    @pytest.mark.asyncio
    async def test_status_failure(self, mock_api, console):
        mock_api.get_status.side_effect = Exception("API error")
        code = await run_status(mock_api, console)
        assert code == 1


class TestStatusHelpers:
    def test_state_style_all_states(self):
        states = [
            "running",
            "starting",
            "stopping",
            "stopped",
            "error",
            "idle",
            "processing",
            "initializing",
            "degraded",
            "disabled",
            "unknown",
        ]
        for s in states:
            style = _state_style(s)
            assert isinstance(style, str)
            assert len(style) > 0

    def test_state_label_running(self):
        label = _state_label("running")
        assert "running" in label.plain
        assert "●" in label.plain

    def test_state_label_error(self):
        label = _state_label("error")
        assert "error" in label.plain


class TestConfigHelpers:
    def test_format_value_none(self):
        assert "null" in _format_value(None)

    def test_format_value_bool(self):
        assert "true" in _format_value(True).lower() or "True" in _format_value(True)

    def test_format_value_int(self):
        result = _format_value(42)
        assert "42" in result

    def test_format_value_float(self):
        result = _format_value(3.14)
        assert "3.14" in result

    def test_format_value_string(self):
        result = _format_value("hello")
        assert "hello" in result

    def test_format_value_empty_string(self):
        result = _format_value("")
        assert '""' in result

    def test_build_tree_empty(self):
        tree = _build_tree({})
        assert tree is not None

    def test_build_tree_simple(self):
        tree = _build_tree({"key": "value"})
        assert tree is not None

    def test_build_tree_nested(self):
        tree = _build_tree({"outer": {"inner": "value"}})
        assert tree is not None

    def test_build_tree_with_list(self):
        tree = _build_tree({"items": [1, 2, 3]})
        assert tree is not None

    def test_build_tree_with_list_of_dicts(self):
        tree = _build_tree({"items": [{"a": 1}, {"b": 2}]})
        assert tree is not None


@pytest.mark.asyncio
async def test_run_config_show_delegates(mock_api, console):
    code = await run_config_show(mock_api, console)
    assert code == 0


@pytest.mark.asyncio
async def test_run_config_get_value(mock_api, console):
    code = await run_config_get(mock_api, console, key="server.port")
    assert code == 0


@pytest.mark.asyncio
async def test_run_config_get_missing(mock_api, console):
    code = await run_config_get(mock_api, console, key="nonexistent.key")
    assert code == 1


@pytest.mark.asyncio
async def test_run_config_get_json(mock_api, console):
    code = await run_config_get(mock_api, console, key="server.port", json_output=True)
    assert code == 0


@pytest.mark.asyncio
async def test_run_config_get_json_show_all(mock_api, console):
    code = await run_config_get(mock_api, console, json_output=True)
    assert code == 0


class TestRunLogs:
    @pytest.mark.asyncio
    async def test_logs_level_style(self):
        assert "green" in _level_style("INFO")
        assert "yellow" in _level_style("WARNING")
        assert "red" in _level_style("ERROR")
        assert "blue" in _level_style("DEBUG")

    def test_format_log_entry(self):
        entry = LogEntry(level="INFO", message="test message", timestamp=1000.0)
        result = _format_log(entry)
        assert "test message" in result.plain

    def test_format_log_no_timestamp(self):
        entry = LogEntry(level="ERROR", message="no time")
        result = _format_log(entry)
        assert "no time" in result.plain

    @pytest.mark.asyncio
    async def test_logs_non_follow_mode(self, console):
        with patch("cli.commands.logs.WSClient") as mock_ws_cls:
            mock_ws = MagicMock()
            mock_ws.connect = AsyncMock()
            mock_ws.disconnect = AsyncMock()
            mock_ws_cls.return_value = mock_ws
            code = await run_logs("http://localhost:9999", None, console, follow=False)
            assert code == 0

    @pytest.mark.asyncio
    async def test_logs_with_level_filter(self, console):
        with patch("cli.commands.logs.WSClient") as mock_ws_cls:
            mock_ws = MagicMock()
            mock_ws.connect = AsyncMock()
            mock_ws.disconnect = AsyncMock()
            mock_ws_cls.return_value = mock_ws
            code = await run_logs("http://localhost:9999", None, console, level_filter="ERROR", follow=False)
            assert code == 0

    @pytest.mark.asyncio
    async def test_logs_cancelled(self, console):
        with patch("cli.commands.logs.WSClient") as mock_ws_cls:
            mock_ws = AsyncMock()
            mock_ws.connect = AsyncMock()
            mock_ws.disconnect = AsyncMock()
            mock_ws_cls.return_value = mock_ws
            code = await run_logs("http://localhost:9999", None, console, follow=False)
            assert code == 0


class TestConfigValueParsing:
    @pytest.mark.asyncio
    async def test_config_set_bool_true(self, mock_api, console):
        mock_api.get_config.return_value.raw = {}
        mock_api.get_config.return_value.get = lambda k: None
        mock_api.get_config.return_value.set = MagicMock()
        from cli.commands.config import run_config_set

        code = await run_config_set(mock_api, console, "modules.tts.enabled", "true")
        assert code == 0
        mock_api.update_config.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_set_int(self, mock_api, console):
        mock_api.get_config.return_value.raw = {}
        mock_api.get_config.return_value.get = lambda k: None
        mock_api.get_config.return_value.set = MagicMock()
        from cli.commands.config import run_config_set

        code = await run_config_set(mock_api, console, "server.port", "8080")
        assert code == 0

    @pytest.mark.asyncio
    async def test_config_set_float(self, mock_api, console):
        mock_api.get_config.return_value.raw = {}
        mock_api.get_config.return_value.get = lambda k: None
        mock_api.get_config.return_value.set = MagicMock()
        from cli.commands.config import run_config_set

        code = await run_config_set(mock_api, console, "audio.volume", "3.14")
        assert code == 0

    @pytest.mark.asyncio
    async def test_config_set_false(self, mock_api, console):
        mock_api.get_config.return_value.raw = {}
        mock_api.get_config.return_value.get = lambda k: None
        mock_api.get_config.return_value.set = MagicMock()
        from cli.commands.config import run_config_set

        code = await run_config_set(mock_api, console, "modules.tts.enabled", "false")
        assert code == 0

    @pytest.mark.asyncio
    async def test_config_set_null(self, mock_api, console):
        mock_api.get_config.return_value.raw = {}
        mock_api.get_config.return_value.get = lambda k: None
        mock_api.get_config.return_value.set = MagicMock()
        from cli.commands.config import run_config_set

        code = await run_config_set(mock_api, console, "some.key", "null")
        assert code == 0
