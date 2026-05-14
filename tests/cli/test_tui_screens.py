from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import MagicMock

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Markdown, Select, Switch

from cli.client.http_client import LogEntry, PipelineStatus
from cli.tui.screens.dashboard import DashboardScreen
from cli.tui.screens.help import HELP_TEXT, HelpScreen
from cli.tui.screens.module_detail import (
    MODULE_CONFIG_SCHEMA,
    MODULE_ICONS,
    MODULE_TITLES,
    ConfigField,
    ModuleConfigForm,
    ModuleDetailScreen,
)
from cli.tui.widgets.header import TUIHeader
from cli.tui.widgets.log_panel import LOG_LEVELS, TUILogPanel
from cli.tui.widgets.metrics_panel import TUIMetricsPanel
from cli.tui.widgets.module_grid import CARD_NAMES, TUIModuleCard, TUIModuleGrid
from cli.tui.widgets.status_bar import TUIStatusBar


# ── Test helpers ──


class _TestApp(App):
    def __init__(self, widget):
        super().__init__()
        self._test_widget = widget

    def compose(self) -> ComposeResult:
        yield self._test_widget


@asynccontextmanager
async def _with_app(widget):
    app = _TestApp(widget)
    async with app.run_test() as pilot:
        yield pilot


# ── HelpScreen ──


class TestHelpScreen:
    def test_help_contains_keyboard_shortcuts(self):
        assert "Space" in HELP_TEXT
        assert "Quit" in HELP_TEXT

    def test_help_mentions_all_keys(self):
        for key in ["Space", "S", "L", "Q", "Esc", "C", "O", "R", "M"]:
            assert key in HELP_TEXT, f"Key '{key}' not in HELP_TEXT"


# ── DashboardScreen (logic-only tests) ──


class TestDashboardScreen:
    def test_dict_to_yaml_simple(self):
        screen = DashboardScreen()
        yaml = screen._dict_to_yaml({"key": "value"})
        assert "key: value" in yaml

    def test_dict_to_yaml_nested(self):
        screen = DashboardScreen()
        yaml = screen._dict_to_yaml({"outer": {"inner": 42}})
        assert "outer:" in yaml
        assert "inner: 42" in yaml

    def test_dict_to_yaml_list(self):
        screen = DashboardScreen()
        yaml = screen._dict_to_yaml({"items": ["a", "b"]})
        assert "items:" in yaml
        assert "- a" in yaml

    def test_dict_to_yaml_bool(self):
        screen = DashboardScreen()
        yaml = screen._dict_to_yaml({"enabled": True})
        assert "true" in yaml.lower()

    def test_dict_to_yaml_none(self):
        screen = DashboardScreen()
        yaml = screen._dict_to_yaml({"key": None})
        assert "null" in yaml

    def test_dict_to_yaml_special_chars_escaped(self):
        screen = DashboardScreen()
        yaml = screen._dict_to_yaml({"key": "hello:world"})
        assert '"hello:world"' in yaml

    def test_yaml_value_bool(self):
        assert DashboardScreen._yaml_value(True) == "true"
        assert DashboardScreen._yaml_value(False) == "false"

    def test_yaml_value_none(self):
        assert DashboardScreen._yaml_value(None) == "null"

    def test_yaml_value_string_needs_quoting(self):
        assert DashboardScreen._yaml_value("hello:world").count('"') >= 2

    def test_yaml_value_simple_string(self):
        assert DashboardScreen._yaml_value("simple") == "simple"

    def test_yaml_value_int(self):
        assert DashboardScreen._yaml_value(42) == "42"

    @pytest.mark.asyncio
    async def test_compose(self):
        screen = DashboardScreen()
        async with _with_app(screen):
            pass


# ── TUIStatusBar (logic-only, needs app for render) ──


class TestTUIStatusBar:
    @pytest.mark.asyncio
    async def test_compose(self):
        sb = TUIStatusBar()
        async with _with_app(sb):
            pass


# ── TUIMetricsPanel ──


class TestTUIMetricsPanel:
    def test_bar_function(self):
        from cli.tui.widgets.metrics_panel import _bar
        result = _bar(50, 100, 20)
        assert any(c in result for c in "█▓▒░")

    def test_sparkline_function(self):
        from cli.tui.widgets.metrics_panel import _sparkline
        result = _sparkline([10, 20, 30, 40, 50], 10)
        assert len(result) == 10

    def test_sparkline_empty(self):
        from cli.tui.widgets.metrics_panel import _sparkline
        result = _sparkline([], 10)
        assert len(result) == 10

    def test_sparkline_single_value(self):
        from cli.tui.widgets.metrics_panel import _sparkline
        result = _sparkline([42], 10)
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_compose(self):
        mp = TUIMetricsPanel()
        async with _with_app(mp):
            pass


# ── TUILogPanel ──


class TestTUILogPanel:
    def test_filter_levels_defined(self):
        assert "ALL" in LOG_LEVELS
        assert "INFO" in LOG_LEVELS
        assert "ERROR" in LOG_LEVELS
        assert "WARNING" in LOG_LEVELS
        assert "DEBUG" in LOG_LEVELS

    def test_level_style_function(self):
        from cli.tui.widgets.log_panel import _level_style
        assert "green" in _level_style("INFO")
        assert "yellow" in _level_style("WARNING")
        assert "red" in _level_style("ERROR")
        assert "blue" in _level_style("DEBUG")

    @pytest.mark.asyncio
    async def test_compose(self):
        lp = TUILogPanel()
        async with _with_app(lp):
            pass


# ── TUIModuleCard ──


class TestTUIModuleCard:
    def test_all_card_names_have_valid_ids(self):
        for name in CARD_NAMES:
            card = TUIModuleCard(name)
            assert hasattr(card, "module_name")

    def test_all_modules_have_schema(self):
        for name in CARD_NAMES:
            assert name in MODULE_CONFIG_SCHEMA, f"Missing schema for {name}"
            assert name in MODULE_TITLES, f"Missing title for {name}"
            assert name in MODULE_ICONS, f"Missing icon for {name}"

    def test_card_state_properties(self):
        card = TUIModuleCard("transcriber")
        card._state = "running"
        card._enabled = True
        card._chunks = 10
        card._last_time = 150.0
        assert card._state == "running"
        assert card._chunks == 10

    def test_card_stores_gpu_info(self):
        card = TUIModuleCard("transcriber")
        card._extra = {"using_gpu": True, "memory_mb": 512.0}
        assert card._extra.get("using_gpu") is True

    @pytest.mark.asyncio
    async def test_compose(self):
        card = TUIModuleCard("transcriber")
        async with _with_app(card):
            assert card.module_name == "transcriber"


# ── TUIModuleGrid ──


class TestTUIModuleGrid:
    def test_card_names_length(self):
        assert len(CARD_NAMES) == 8

    def test_first_and_last_names(self):
        assert CARD_NAMES[0] == "input"
        assert CARD_NAMES[-1] == "video_muxer"

    def test_update_modules_empty(self):
        grid = TUIModuleGrid()
        grid.update_modules([])

    def test_update_modules_normal(self):
        grid = TUIModuleGrid()
        grid.update_modules([
            {"name": "transcriber", "state": "running", "enabled": True, "processed_chunks": 10, "last_process_time_ms": 150.0},
        ])

    def test_update_modules_output_mapped(self):
        grid = TUIModuleGrid()
        grid.update_modules([
            {"name": "output", "state": "running", "enabled": True, "processed_chunks": 5, "last_process_time_ms": 100.0},
        ])

    def test_messages(self):
        from cli.tui.widgets.module_grid import CardClicked, ModuleSelected
        assert CardClicked("tts_engine").module_name == "tts_engine"
        assert ModuleSelected("transcriber").module_name == "transcriber"

    @pytest.mark.asyncio
    async def test_compose(self):
        grid = TUIModuleGrid()
        async with _with_app(grid):
            pass


# ── ConfigField ──


class TestConfigField:
    def test_bool_type(self):
        field = ConfigField("Enabled", "enabled", bool, (), "True")
        assert field.field_type == bool

    def test_select_options(self):
        field = ConfigField("Model", "model", str, ("tiny", "small"), "tiny")
        assert len(field.options) == 2

    def test_input_field(self):
        field = ConfigField("CRF", "video_crf", int, (), "")
        assert field.key == "video_crf"

    def test_initial_value(self):
        field = ConfigField("Enabled", "enabled", bool, (), "True")
        assert field._initial_value == "True"


# ── ModuleConfigSchema ──


class TestModuleConfigSchema:
    def test_all_modules_have_schema(self):
        for name in CARD_NAMES:
            assert name in MODULE_CONFIG_SCHEMA

    def test_all_schemas_have_fields(self):
        for name in CARD_NAMES:
            assert len(MODULE_CONFIG_SCHEMA[name]) > 0, f"Empty schema for {name}"

    def test_schema_field_types(self):
        for name in CARD_NAMES:
            for _, _, ftype, _ in MODULE_CONFIG_SCHEMA[name]:
                assert ftype in (bool, str, int, float)

    def test_get_nested_flat_key(self):
        form = ModuleConfigForm("transcriber", None, {})
        assert form._get_nested("model", {"model": "tiny"}) == "tiny"

    def test_get_nested_missing_key(self):
        form = ModuleConfigForm("transcriber", None, {})
        assert form._get_nested("nonexistent", {"model": "tiny"}) is None

    def test_collect_values_empty(self):
        form = ModuleConfigForm("transcriber", None, {"modules": {"transcriber": {}}})
        assert isinstance(form._collect_values(), dict)

    def test_form_module_name(self):
        form = ModuleConfigForm("transcriber", None, {})
        assert form.module_name == "transcriber"

    def test_form_config_access(self):
        form = ModuleConfigForm("transcriber", None, {"modules": {"transcriber": {"enabled": True}}})
        assert form.module_config.get("enabled") is True


class TestModuleConfigMessages:
    def test_config_saved_message(self):
        from cli.tui.screens.module_detail import ModuleConfigSaved
        msg = ModuleConfigSaved("transcriber", {"enabled": True})
        assert msg.module_name == "transcriber"

    def test_toggle_request_message(self):
        from cli.tui.screens.module_detail import ModuleToggleRequest
        assert ModuleToggleRequest("tts_engine").module_name == "tts_engine"

    def test_back_message(self):
        from cli.tui.screens.module_detail import ModuleDetailBack
        assert ModuleDetailBack() is not None


class TestModuleDetailScreen:
    def test_init(self):
        screen = ModuleDetailScreen("transcriber", None, {"modules": {"transcriber": {}}}, MagicMock())
        assert screen.module_name == "transcriber"
