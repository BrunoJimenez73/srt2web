"""Tests for CLI commands using mocked API client."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from rich.console import Console

from cli.commands.config import run_config_get, run_config_set
from cli.commands.status import _state_label, _state_style


class TestStatusHelpers:
    def test_state_style_running(self):
        assert "green" in _state_style("running")

    def test_state_style_error(self):
        assert "red" in _state_style("error")

    def test_state_style_unknown(self):
        assert "white" in _state_style("unknown")

    def test_state_label_running(self):
        label = _state_label("running")
        assert "running" in label.plain


@pytest.mark.asyncio
async def test_config_get_value():
    api = MagicMock()
    api.get_config = AsyncMock()
    api.get_config.return_value = MagicMock()
    api.get_config.return_value.get = lambda k: 9999 if k == "server.port" else None

    console = Console()
    code = await run_config_get(api, console, key="server.port")
    assert code == 0


@pytest.mark.asyncio
async def test_config_get_missing():
    api = MagicMock()
    api.get_config = AsyncMock()
    api.get_config.return_value = MagicMock()
    api.get_config.return_value.get = lambda k: None

    console = Console()
    code = await run_config_get(api, console, key="nonexistent.key")
    assert code == 1


@pytest.mark.asyncio
async def test_config_set_bool():
    api = MagicMock()
    api.get_config = AsyncMock()
    config_data = MagicMock()
    config_data.raw = {}
    config_data.set = MagicMock()
    api.get_config.return_value = config_data
    api.update_config = AsyncMock(return_value={"status": "updated"})

    console = Console()
    code = await run_config_set(api, console, "modules.tts.enabled", "true")
    assert code == 0


@pytest.mark.asyncio
async def test_config_set_int():
    api = MagicMock()
    api.get_config = AsyncMock()
    config_data = MagicMock()
    config_data.raw = {}
    config_data.set = MagicMock()
    api.get_config.return_value = config_data
    api.update_config = AsyncMock(return_value={"status": "updated"})

    console = Console()
    code = await run_config_set(api, console, "server.port", "8080")
    assert code == 0


@pytest.mark.asyncio
async def test_config_get_json():
    api = MagicMock()
    api.get_config = AsyncMock()
    api.get_config.return_value = MagicMock()
    api.get_config.return_value.raw = {"server": {"port": 9999}}
    api.get_config.return_value.get = lambda k: 9999 if k == "server.port" else None

    console = Console()
    code = await run_config_get(api, console, key="server.port", json_output=True)
    assert code == 0
