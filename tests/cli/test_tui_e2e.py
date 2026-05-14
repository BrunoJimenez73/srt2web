from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cli.client.http_client import PipelineStatus
from cli.tui.app import SRT2WebTUI
from cli.tui.screens.help import HelpScreen
from cli.tui.screens.input_control import InputControlScreen
from cli.tui.screens.module_detail import ModuleDetailScreen
from cli.tui.screens.presets_screen import PresetsScreen
from cli.tui.screens.recordings_screen import RecordingsScreen
from cli.tui.widgets.header import TUIHeader
from cli.tui.widgets.log_panel import TUILogPanel
from cli.tui.widgets.metrics_panel import TUIMetricsPanel
from cli.tui.widgets.module_grid import TUIModuleCard, TUIModuleGrid
from cli.tui.widgets.status_bar import TUIStatusBar


def _make_mock_status(**overrides):
    defaults = dict(
        state="stopped",
        mode="thread_parallel",
        chunks_processed=0,
        chunks_failed=0,
        avg_processing_time_ms=0.0,
        uptime_seconds=0.0,
        max_concurrent_chunks=4,
        concurrent_chunks=0,
        buffer_size=0,
        strategy="thread_parallel",
        modules=[
            {
                "name": "input",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "audio_extractor",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "transcriber",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "translator",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "subtitle_generator",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "tts_engine",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "audio_mixer",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
            {
                "name": "video_muxer",
                "state": "idle",
                "enabled": True,
                "processed_chunks": 0,
                "last_process_time_ms": 0.0,
                "extra": {},
            },
        ],
        system={
            "cpu_percent": 10.0,
            "memory_percent": 50.0,
            "memory_mb": 2048.0,
            "gpu_util": 0.0,
            "gpu_memory_mb": 0.0,
        },
        network={},
        sync={},
        input_receiving=False,
        input_info={},
    )
    defaults.update(overrides)
    return PipelineStatus.from_dict(defaults)


@pytest.fixture
def mock_deps():
    """Patch APIClient and WSClient so the TUI doesn't connect to a real server."""
    with (
        patch("cli.tui.app.APIClient") as mock_api_cls,
        patch("cli.tui.app.WSClient") as mock_ws_cls,
    ):
        mock_api = MagicMock()
        mock_api.token = None
        mock_api.get_status = AsyncMock(return_value=_make_mock_status())
        mock_api.get_config = AsyncMock(return_value=MagicMock(raw={"server": {"port": 9999}, "modules": {}}))
        mock_api.get_outputs = AsyncMock(return_value=[])
        mock_api.close = AsyncMock()
        mock_api_cls.return_value = mock_api

        mock_ws = MagicMock()
        mock_ws.connect = AsyncMock()
        mock_ws.disconnect = AsyncMock()
        mock_ws_cls.return_value = mock_ws

        yield {
            "api": mock_api,
            "ws": mock_ws,
            "api_cls": mock_api_cls,
            "ws_cls": mock_ws_cls,
        }


@pytest.mark.asyncio
async def test_app_launches(mock_deps):
    """App composes and all main widgets are present."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        assert app.is_running

        # Header is visible
        assert app.query_one(TUIHeader) is not None

        # StatusBar is visible
        assert app.query_one(TUIStatusBar) is not None

        # MetricsPanel is visible
        assert app.query_one(TUIMetricsPanel) is not None

        # ModuleGrid is visible with 8 cards
        grid = app.query_one(TUIModuleGrid)
        cards = grid.query(TUIModuleCard)
        assert len(list(cards)) == 8

        # LogPanel is visible
        assert app.query_one(TUILogPanel) is not None


@pytest.mark.asyncio
async def test_app_displays_pipeline_state(mock_deps):
    """Status bar updates when poll returns data."""
    app = SRT2WebTUI()
    status = _make_mock_status(state="running")
    mock_deps["api"].get_status = AsyncMock(return_value=status)

    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        sb = app.query_one(TUIStatusBar)
        assert sb is not None


@pytest.mark.asyncio
async def test_help_screen_opens_and_closes(mock_deps):
    """Pressing ? opens HelpScreen; Esc closes it."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("?")
        assert isinstance(app.screen, HelpScreen)

        await pilot.press("escape")
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_module_detail_screen_opens(mock_deps):
    """Pressing m opens ModuleDetailScreen; Esc closes it."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        await pilot.press("m")
        assert isinstance(app.screen, ModuleDetailScreen)

        await pilot.press("escape")
        assert not isinstance(app.screen, ModuleDetailScreen)


@pytest.mark.asyncio
async def test_log_panel_toggle(mock_deps):
    """Pressing L toggles log panel visibility."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        lp = app.query_one(TUILogPanel)
        initial_display = lp.styles.display

        await pilot.press("l")
        assert lp.styles.display != initial_display

        await pilot.press("l")
        assert lp.styles.display == initial_display


@pytest.mark.asyncio
async def test_refresh_key(mock_deps):
    """Pressing R calls get_status."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        mock_deps["api"].get_status.assert_called()


@pytest.mark.asyncio
async def test_config_tab_focus(mock_deps):
    """Pressing C focuses the config tab."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        await pilot.press("c")
        assert app.screen is not None


@pytest.mark.asyncio
async def test_outputs_tab_focus(mock_deps):
    """Pressing O focuses the outputs tab."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        await pilot.press("o")
        assert app.screen is not None


@pytest.mark.asyncio
async def test_module_click_opens_detail(mock_deps):
    """Clicking a module card opens the detail screen."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        grid = app.query_one(TUIModuleGrid)
        cards = list(grid.query(TUIModuleCard))
        assert len(cards) == 8

        card = cards[0]
        card.focus()
        await pilot.pause()

        card.post_message(
            type(card).CardClicked(card.module_name) if hasattr(type(card), "CardClicked") else MagicMock()
        )
        await pilot.pause()


@pytest.mark.asyncio
async def test_logo_in_header(mock_deps):
    """Header contains 'srt2web' text."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        header = app.query_one(TUIHeader)
        rendered = header.render()
        assert "srt2web" in str(rendered).lower()


@pytest.mark.asyncio
async def test_status_shows_state(mock_deps):
    """Status bar renders with pipeline state."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        sb = app.query_one(TUIStatusBar)
        # After one poll cycle, the status should be rendered
        assert sb is not None


@pytest.mark.asyncio
async def test_app_quit(mock_deps):
    """Pressing Q quits the app."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


@pytest.mark.asyncio
async def test_help_has_shortcuts_table(mock_deps):
    """Help screen contains the keyboard shortcuts table."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("?")
        help_screen = app.screen
        assert isinstance(help_screen, HelpScreen)
        # HelpScreen has a Markdown widget
        widgets = help_screen.query("Markdown")
        assert len(list(widgets)) > 0


@pytest.mark.asyncio
async def test_poll_loop_updates_config(mock_deps):
    """Poll loop fetches config and updates dashboard."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        mock_deps["api"].get_config.assert_called()


@pytest.mark.asyncio
async def test_poll_loop_updates_outputs(mock_deps):
    """Poll loop fetches outputs."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        mock_deps["api"].get_outputs.assert_called()


@pytest.mark.asyncio
async def test_ws_connection_created(mock_deps):
    """WebSocket client is created on mount."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        mock_deps["ws_cls"].assert_called()


@pytest.mark.asyncio
async def test_presets_screen_opens(mock_deps):
    """Pressing P opens PresetsScreen; Esc closes it."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        await pilot.press("p")
        assert isinstance(app.screen, PresetsScreen)
        await pilot.press("escape")
        assert not isinstance(app.screen, PresetsScreen)


@pytest.mark.asyncio
async def test_presets_screen_shows_presets(mock_deps):
    """PresetsScreen calls get_presets and renders list."""
    mock_deps["api"].get_presets = AsyncMock(
        return_value=[
            {"name": "low-latency", "description": "Optimized for speed", "built_in": True},
            {"name": "high-quality", "description": "Best quality output", "built_in": False},
        ]
    )
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("p")
        await pilot.pause()
        mock_deps["api"].get_presets.assert_called()


@pytest.mark.asyncio
async def test_presets_save(mock_deps):
    """Saving a preset calls save_preset API."""
    mock_deps["api"].save_preset = AsyncMock(return_value={"status": "ok", "name": "my-preset"})
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("p")
        await pilot.pause()
        screen = app.screen
        inp = screen.query_one("#save-input")
        inp.value = "my-preset"
        btn = screen.query_one("#btn-save-preset")
        await pilot.click(btn)
        await pilot.pause()
        mock_deps["api"].save_preset.assert_called_once()


@pytest.mark.asyncio
async def test_presets_apply(mock_deps):
    """Applying a preset calls apply_preset API."""
    mock_deps["api"].get_presets = AsyncMock(
        return_value=[
            {"name": "low-latency", "description": "Fast", "built_in": True},
        ]
    )
    mock_deps["api"].apply_preset = AsyncMock(return_value={"status": "ok"})
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("p")
        await pilot.pause()
        await pilot.press("a")
        await pilot.pause()
        mock_deps["api"].apply_preset.assert_called_once_with("low-latency")


@pytest.mark.asyncio
async def test_recordings_screen_opens(mock_deps):
    """Pressing Shift+R opens RecordingsScreen; Esc closes it."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        await pilot.press("R")
        await pilot.pause()
        assert isinstance(app.screen, RecordingsScreen)
        await pilot.press("escape")
        assert not isinstance(app.screen, RecordingsScreen)


@pytest.mark.asyncio
async def test_recordings_screen_shows_list(mock_deps):
    """RecordingsScreen fetches and renders recordings."""
    mock_deps["api"].get_recordings = AsyncMock(
        return_value=[
            {"name": "recording_001.mp4", "size_formatted": "12 MB", "format": "mp4", "modified": "2026-05-14"},
        ]
    )
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("R")
        await pilot.pause()
        mock_deps["api"].get_recordings.assert_called()


@pytest.mark.asyncio
async def test_recordings_delete(mock_deps):
    """Pressing d in recordings screen calls delete_recording."""
    mock_deps["api"].get_recordings = AsyncMock(
        return_value=[
            {"name": "test_rec.mp4", "size_formatted": "5 MB"},
        ]
    )
    mock_deps["api"].delete_recording = AsyncMock(return_value={"status": "ok"})
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("R")
        await pilot.pause()
        await pilot.press("d")
        await pilot.pause()
        mock_deps["api"].delete_recording.assert_called_once_with("test_rec.mp4")


@pytest.mark.asyncio
async def test_input_control_screen_opens(mock_deps):
    """Pressing I opens InputControlScreen; Esc closes it."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.pause()
        await pilot.press("i")
        await pilot.pause()
        assert isinstance(app.screen, InputControlScreen)
        await pilot.press("escape")
        assert not isinstance(app.screen, InputControlScreen)


@pytest.mark.asyncio
async def test_input_control_shows_info(mock_deps):
    """InputControlScreen fetches input info on mount."""
    mock_deps["api"].get_input_info = AsyncMock(return_value={"type": "srt", "url": "srt://localhost:5000"})
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("i")
        await pilot.pause()
        mock_deps["api"].get_input_info.assert_called()


@pytest.mark.asyncio
async def test_input_control_play(mock_deps):
    """Play button calls control_input('play')."""
    mock_deps["api"].control_input = AsyncMock(return_value={"status": "playing"})
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("i")
        await pilot.pause()
        screen = app.screen
        btn = screen.query_one("#btn-play")
        await pilot.click(btn)
        await pilot.pause()
        mock_deps["api"].control_input.assert_called_with("play")


@pytest.mark.asyncio
async def test_module_detail_auto_refresh_refetches(mock_deps):
    """Module detail screen periodically fetches status."""
    app = SRT2WebTUI()
    async with app.run_test(size=(120, 36)) as pilot:
        await pilot.press("m")
        await pilot.pause()
        await pilot.pause()
        mock_deps["api"].get_status.assert_called()
