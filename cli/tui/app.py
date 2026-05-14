from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import asdict

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer

from cli.client.http_client import APIClient, LogEntry, ModuleInfo, PipelineStatus
from cli.client.ws_client import WSClient
from cli.tui.screens.dashboard import DashboardScreen
from cli.tui.screens.help import HelpScreen
from cli.tui.screens.module_detail import ModuleDetailScreen
from cli.tui.widgets.module_grid import CARD_NAMES, ModuleSelected

logger = logging.getLogger("srt2web.tui")


def _log_error_on_done(task: asyncio.Task) -> None:
    ex = task.exception()
    if ex:
        logger.error("Background task failed: %s", ex)


class SRT2WebTUI(App):
    CSS = """
    DashboardScreen {
        align: center top;
    }

    #left-col {
        width: 40%;
        height: 100%;
    }

    #right-col {
        width: 60%;
        height: 100%;
    }

    TUIStatusBar {
        height: 7;
        border: solid $primary;
        margin: 0 1;
    }

    TUIMetricsPanel {
        height: 7;
        border: solid $primary;
        margin: 0 1;
    }

    TUIModuleGrid {
        height: 12;
        border: solid $primary;
        margin: 0 1;
    }

    TabbedContent {
        height: 12;
        border: solid $primary;
        margin: 0 1;
    }

    TUILogPanel {
        height: 10;
        border: solid $primary;
        margin: 0 1 1 1;
    }

    TUIHeader {
        height: 1;
    }

    TUIModuleCard {
        width: 1fr;
        height: 5;
        border: solid $border;
        margin: 0 1;
        padding: 0 1;
    }

    TUIModuleCard:focus {
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("space", "toggle_pipeline", "Start/Stop"),
        Binding("s", "save_config", "Save"),
        Binding("l", "toggle_logs", "Logs"),
        Binding("?", "show_help", "Help"),
        Binding("r", "refresh", "Refresh"),
        Binding("c", "focus_config", "Config"),
        Binding("o", "focus_outputs", "Outputs"),
        Binding("m", "open_module", "Module"),
    ]
    if sys.platform == "darwin":
        BINDINGS.insert(0, Binding("ctrl+q", "quit", "Quit (macOS)"))

    def __init__(self, server: str = "http://localhost:9999", token: str | None = None):
        super().__init__()
        self.server = server
        self.api = APIClient(server, token)
        self.ws: WSClient | None = None
        self._polling_task: asyncio.Task | None = None
        self.status: PipelineStatus | None = None
        self.logs: list[LogEntry] = []
        self.ws_connected = reactive(False)
        self.pipeline_state = reactive("stopped")
        self._config_data: dict | None = None
        self._last_module_index = 0

    def compose(self) -> ComposeResult:
        yield DashboardScreen()
        yield Footer()

    def on_mount(self) -> None:
        self._polling_task = asyncio.create_task(self._poll_loop())
        self._polling_task.add_done_callback(_log_error_on_done)
        ws_task = asyncio.create_task(self._connect_ws())
        ws_task.add_done_callback(_log_error_on_done)

    async def _connect_ws(self) -> None:
        self.ws = WSClient(
            url=self.server,
            token=self.api.token,
            on_log=self._on_ws_log,
            on_status=self._on_ws_status,
            on_connection_change=self._on_ws_connection,
        )
        await self.ws.connect()

    def _on_ws_log(self, entry: LogEntry) -> None:
        self.logs.append(entry)
        if len(self.logs) > 5000:
            self.logs = self.logs[-3000:]
        dashboard = self.query_one(DashboardScreen)
        dashboard.update_logs(self.logs)

    def _on_ws_status(self, data: dict) -> None:
        if not data:
            return
        try:
            self.status = PipelineStatus.from_dict(data)
            self.pipeline_state = self.status.state
            dashboard = self.query_one(DashboardScreen)
            dashboard.update_status(self.status)
            dashboard.update_metrics(self.status.system)
            dashboard.update_modules(self.status.modules)
        except Exception:
            logger.warning("Failed to process WS status update", exc_info=True)

    def _on_ws_connection(self, connected: bool) -> None:
        self.ws_connected = connected
        try:
            dashboard = self.query_one(DashboardScreen)
            h = dashboard.query_one("#tui-header")
            h.ws_connected = connected
        except Exception:
            logger.debug("Header not yet mounted on WS connection change")

    async def _poll_loop(self) -> None:
        while True:
            delay = 5.0
            try:
                dashboard = self.query_one(DashboardScreen)
            except Exception:
                await asyncio.sleep(1.0)
                continue

            try:
                self.status = await self.api.get_status()
                self.pipeline_state = self.status.state
                dashboard.update_status(self.status)
                dashboard.update_metrics(self.status.system)
                dashboard.update_modules(self.status.modules)
                delay = 1.0 if self.status.state == "running" else 3.0
            except Exception as e:
                logger.debug("Poll status failed: %s", e)

            try:
                config_data = await self.api.get_config()
                self._config_data = config_data.raw
                dashboard.update_config(config_data.raw)
            except Exception as e:
                logger.debug("Poll config failed: %s", e)

            try:
                outputs = await self.api.get_outputs()
                dashboard.update_outputs([asdict(o) for o in outputs])
            except Exception as e:
                logger.debug("Poll outputs failed: %s", e)

            await asyncio.sleep(delay)

    def action_toggle_pipeline(self) -> None:
        task = asyncio.create_task(self._toggle_pipeline())
        task.add_done_callback(_log_error_on_done)

    async def _toggle_pipeline(self) -> None:
        if not self.status:
            self.app.notify("No status available yet", severity="warning", timeout=3)
            return
        try:
            if self.status.state in ("running", "starting"):
                result = await self.api.stop_pipeline()
                self.app.notify("Pipeline stopped", severity="information", timeout=3)
            else:
                result = await self.api.start_pipeline()
                self.app.notify("Pipeline started", severity="information", timeout=3)
        except Exception as e:
            self.app.notify(f"Toggle failed: {e}", severity="error", timeout=5)
            logger.error("Toggle pipeline failed: %s", e)

    def action_save_config(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        task = asyncio.create_task(dashboard.save_config())
        task.add_done_callback(_log_error_on_done)

    def action_toggle_logs(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        dashboard.toggle_logs()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_focus_config(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        dashboard.focus_config()

    def on_module_selected(self, event: ModuleSelected) -> None:
        self._last_module_index = (
            CARD_NAMES.index(event.module_name) if event.module_name in CARD_NAMES else self._last_module_index
        )
        self.action_open_module(event.module_name)

    def action_open_module(self, module_name: str | None = None) -> None:
        if module_name is None:
            module_name = CARD_NAMES[self._last_module_index]

        module_info_dict = None
        if self.status:
            for m in self.status.modules:
                if m.get("name") == module_name:
                    module_info_dict = m
                    break

        module_info: ModuleInfo | None = None
        if module_info_dict:
            module_info = ModuleInfo.from_dict(module_info_dict)

        screen = ModuleDetailScreen(
            module_name,
            module_info,
            self._config_data or {},
            self.api,
        )
        self.push_screen(screen)

    def action_focus_outputs(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        dashboard.focus_outputs()

    async def action_refresh(self) -> None:
        try:
            self.status = await self.api.get_status()
            dashboard = self.query_one(DashboardScreen)
            dashboard.update_status(self.status)
            dashboard.update_metrics(self.status.system)
            dashboard.update_modules(self.status.modules)
            self.app.notify("Refreshed", severity="information", timeout=1)
        except Exception as e:
            self.app.notify(f"Refresh failed: {e}", severity="error", timeout=3)
            logger.error("Refresh failed: %s", e)

    def on_unmount(self) -> None:
        if self._polling_task:
            self._polling_task.cancel()
        if self.ws:
            task = asyncio.create_task(self.ws.disconnect())
            task.add_done_callback(_log_error_on_done)
        task = asyncio.create_task(self.api.close())
        task.add_done_callback(_log_error_on_done)


def run_tui(server: str = "http://localhost:9999", token: str | None = None) -> None:
    app = SRT2WebTUI(server=server, token=token)
    app.run()
