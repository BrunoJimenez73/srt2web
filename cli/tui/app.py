from __future__ import annotations

import asyncio
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer

from dataclasses import asdict

from cli.client.http_client import APIClient, LogEntry, ModuleInfo, OutputInfo, PipelineStatus
from cli.client.ws_client import WSClient
from cli.tui.screens.dashboard import DashboardScreen
from cli.tui.screens.help import HelpScreen
from cli.tui.screens.login import LoginScreen
from cli.tui.screens.module_detail import ModuleDetailScreen
from cli.tui.widgets.module_grid import CARD_NAMES, ModuleSelected


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
        self._module_info_map: dict[str, ModuleInfo] = {}
        self._config_data: dict | None = None
        self._last_module_index = 0

    def compose(self) -> ComposeResult:
        yield DashboardScreen()
        yield Footer()

    def on_mount(self) -> None:
        self._polling_task = asyncio.create_task(self._poll_loop())
        asyncio.create_task(self._connect_ws())

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
        pass

    def _on_ws_connection(self, connected: bool) -> None:
        self.ws_connected = connected
        try:
            dashboard = self.query_one(DashboardScreen)
            h = dashboard.query_one("#tui-header")
            h.ws_connected = connected
        except Exception:
            pass

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
                pass

            try:
                config_data = await self.api.get_config()
                self._config_data = config_data.raw
                dashboard.update_config(config_data.raw)
            except Exception:
                pass

            try:
                outputs = await self.api.get_outputs()
                dashboard.update_outputs([asdict(o) for o in outputs])
            except Exception:
                pass

            await asyncio.sleep(delay)

    def action_toggle_pipeline(self) -> None:
        asyncio.create_task(self._toggle_pipeline())

    async def _toggle_pipeline(self) -> None:
        if not self.status:
            return
        try:
            if self.status.state in ("running", "starting"):
                await self.api.stop_pipeline()
            else:
                await self.api.start_pipeline()
        except Exception:
            pass

    def action_save_config(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        asyncio.create_task(dashboard.save_config())

    def action_toggle_logs(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        dashboard.toggle_logs()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_focus_config(self) -> None:
        dashboard = self.query_one(DashboardScreen)
        dashboard.focus_config()

    def on_module_selected(self, event: ModuleSelected) -> None:
        self._last_module_index = CARD_NAMES.index(event.module_name) if event.module_name in CARD_NAMES else self._last_module_index
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
        except Exception:
            pass

    def on_unmount(self) -> None:
        if self._polling_task:
            self._polling_task.cancel()
        if self.ws:
            asyncio.create_task(self.ws.disconnect())
        asyncio.create_task(self.api.close())


def run_tui(server: str = "http://localhost:9999", token: str | None = None) -> None:
    app = SRT2WebTUI(server=server, token=token)
    app.run()
