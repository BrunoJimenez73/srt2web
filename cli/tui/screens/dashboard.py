from __future__ import annotations

from typing import Any

from rich.syntax import Syntax
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static, TabbedContent, TabPane

from cli.client.http_client import LogEntry, PipelineStatus
from cli.tui.widgets.header import TUIHeader
from cli.tui.widgets.log_panel import TUILogPanel
from cli.tui.widgets.metrics_panel import TUIMetricsPanel
from cli.tui.widgets.module_grid import TUIModuleGrid
from cli.tui.widgets.status_bar import TUIStatusBar


class DashboardScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield TUIHeader(id="tui-header")
            with Horizontal():
                with Vertical(id="left-col"):
                    yield TUIStatusBar(id="status-bar")
                    yield TUIMetricsPanel(id="metrics-panel")
                with Vertical(id="right-col"):
                    yield TUIModuleGrid(id="module-grid")
                    with TabbedContent(initial="config"):
                        with TabPane("Config", id="config"):
                            yield Static("Loading config...", id="config-tree", markup=True)
                        with TabPane("Outputs", id="outputs"):
                            yield Static("Loading outputs...", id="outputs-list", markup=True)
            yield TUILogPanel(id="log-panel")

    def on_mount(self) -> None:
        self._config_data: dict | None = None

    def update_status(self, status: PipelineStatus) -> None:
        sb = self.query_one("#status-bar", TUIStatusBar)
        sb.update_status(status)

        h = self.query_one("#tui-header", TUIHeader)
        if hasattr(status, "state"):
            h.pipeline_state = status.state

    def update_metrics(self, system: dict) -> None:
        mp = self.query_one("#metrics-panel", TUIMetricsPanel)
        mp.update_metrics(system)

    def update_modules(self, modules: list[dict]) -> None:
        mg = self.query_one("#module-grid", TUIModuleGrid)
        mg.update_modules(modules)

    def update_config(self, config_data: dict) -> None:
        self._config_data = config_data
        tree_widget = self.query_one("#config-tree", Static)
        syntax = Syntax(
            self._dict_to_yaml(config_data),
            "yaml",
            theme="monokai",
            word_wrap=True,
        )
        tree_widget.update(syntax)

    def update_outputs(self, outputs: list[dict]) -> None:
        out_widget = self.query_one("#outputs-list", Static)
        lines = []
        for o in outputs:
            state = o.get("state", "?")
            enabled = o.get("enabled", True)
            name = o.get("name", "?")
            otype = o.get("type", "?")
            icon = "✓" if enabled else "✗"
            lines.append(f"{icon} [bold]{name}[/] ({otype}) — [italic]{state}[/]")
        if not lines:
            lines.append("[dim]No outputs configured[/]")
        out_widget.update("\n".join(lines))

    def update_logs(self, logs: list[LogEntry]) -> None:
        lp = self.query_one("#log-panel", TUILogPanel)
        lp.update_logs(logs)

    def toggle_logs(self) -> None:
        lp = self.query_one("#log-panel", TUILogPanel)
        if lp.styles.display == "none":
            lp.styles.display = "block"
        else:
            lp.styles.display = "none"

    def focus_config(self) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = "config"

    def focus_outputs(self) -> None:
        tabs = self.query_one(TabbedContent)
        tabs.active = "outputs"

    async def save_config(self) -> None:
        if self._config_data:
            app = self.app
            try:
                await app.api.update_config(self._config_data)
                self.notify("Config saved", severity="information", timeout=3)
            except Exception as e:
                self.notify(f"Error saving config: {e}", severity="error", timeout=5)

    def _dict_to_yaml(self, d: dict, indent: int = 0) -> str:
        lines = []
        prefix = "  " * indent
        for k, v in d.items():
            if isinstance(v, dict):
                lines.append(f"{prefix}{k}:")
                lines.append(self._dict_to_yaml(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{prefix}{k}:")
                for item in v:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}-")
                        lines.append(self._dict_to_yaml(item, indent + 2))
                    else:
                        lines.append(f"{prefix}- {self._yaml_value(item)}")
            else:
                lines.append(f"{prefix}{k}: {self._yaml_value(v)}")
        return "\n".join(lines)

    @staticmethod
    def _yaml_value(v: Any) -> str:
        if v is None:
            return "null"
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, str):
            needs_quoting = any(
                c in v
                for c in (
                    ":",
                    "#",
                    "{",
                    "}",
                    "[",
                    "]",
                    ",",
                    "&",
                    "*",
                    "?",
                    "|",
                    "-",
                    "<",
                    ">",
                    "=",
                    "!",
                    "%",
                    "@",
                    "`",
                    "'",
                    '"',
                )
            )
            needs_quoting = (
                needs_quoting
                or not v
                or v[0] in ("'", '"')
                or v.lower() in ("true", "false", "null", "yes", "no", "on", "off")
            )
            if needs_quoting:
                escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escaped}"'
            return v
        return str(v)
