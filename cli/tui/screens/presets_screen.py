from __future__ import annotations

from typing import Any

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer
from textual.screen import Screen
from textual.widgets import Button, Input, Static


class PresetsScreen(Screen):
    CSS = """
    Screen {
        background: $surface;
    }

    .screen-title {
        color: $text;
        text-style: bold;
        padding: 1 2;
        margin-bottom: 1;
    }

    .preset-item {
        height: 3;
        padding: 0 2;
        border: solid $border;
        margin: 0 1 1 1;
    }

    .preset-item:hover {
        border: solid $accent;
    }

    .preset-name {
        color: $text;
        text-style: bold;
    }

    .preset-desc {
        color: $text-muted;
    }

    .action-bar {
        height: 3;
        margin: 1 2;
    }

    .save-area {
        height: 5;
        margin: 1 2;
        border: solid $border;
        padding: 1;
    }

    #preset-list {
        height: 1fr;
    }

    #save-input {
        width: 60%;
    }
    """

    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("a", "apply_preset", "Apply"),
        ("d", "delete_preset", "Delete"),
    ]

    def __init__(self, api_client: Any):
        super().__init__()
        self.api_client = api_client
        self._presets: list[dict] = []
        self._selected: int = 0

    def compose(self) -> ComposeResult:
        yield Static("Presets Management", classes="screen-title")
        with ScrollableContainer(id="preset-list"):
            yield Static("Loading presets...", id="presets-content")
        with Horizontal(classes="save-area"):
            yield Input(placeholder="New preset name...", id="save-input")
            yield Button("Save", id="btn-save-preset", variant="primary")
        with Horizontal(classes="action-bar"):
            yield Button("Refresh", id="btn-refresh")
            yield Button("Back", id="btn-back", variant="default")

    async def on_mount(self) -> None:
        await self._load_presets()

    async def _load_presets(self) -> None:
        try:
            presets = await self.api_client.get_presets()
            self._presets = presets if isinstance(presets, list) else presets.get("presets", [])
        except Exception as e:
            self.app.notify(f"Error loading presets: {e}", severity="error", timeout=5)
            self._presets = []
        self._render_presets()

    def _render_presets(self) -> None:
        content = self.query_one("#presets-content", Static)
        if not self._presets:
            content.update(Text("No presets available. Save current config as a preset.", style="dim"))
            return

        t = Text()
        for i, p in enumerate(self._presets):
            name = p.get("name", "?")
            desc = p.get("description", "")
            builtin = p.get("built_in", False)
            marker = " [built-in]" if builtin else ""
            prefix = "▸ " if i == self._selected else "  "
            t.append(f"{prefix}{name}{marker}\n", style="bold" if i == self._selected else "")
            if desc:
                t.append(f"    {desc}\n", style="dim")
            t.append("\n")

        # Add key hints
        t.append("\n[dim]Keys: [A]pply  [D]elete  [Esc] Back[/]")
        content.update(t)

    @on(Button.Pressed, "#btn-save-preset")
    async def on_save_preset(self) -> None:
        inp = self.query_one("#save-input", Input)
        name = inp.value.strip()
        if not name:
            self.app.notify("Enter a preset name", severity="warning", timeout=3)
            return
        try:
            result = await self.api_client.save_preset(name)
            self.app.notify(f"Preset '{name}' saved", severity="information", timeout=3)
            inp.value = ""
            await self._load_presets()
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=5)

    @on(Button.Pressed, "#btn-refresh")
    async def on_refresh(self) -> None:
        await self._load_presets()

    @on(Button.Pressed, "#btn-back")
    def on_back(self) -> None:
        self.app.pop_screen()

    async def action_apply_preset(self) -> None:
        if not self._presets:
            self.app.notify("No presets to apply", severity="warning", timeout=3)
            return
        name = self._presets[self._selected].get("name", "")
        try:
            await self.api_client.apply_preset(name)
            self.app.notify(f"Preset '{name}' applied", severity="information", timeout=3)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=5)

    async def action_delete_preset(self) -> None:
        if not self._presets:
            self.app.notify("No presets to delete", severity="warning", timeout=3)
            return
        p = self._presets[self._selected]
        name = p.get("name", "")
        if p.get("built_in", False):
            self.app.notify("Cannot delete built-in presets", severity="warning", timeout=3)
            return
        try:
            await self.api_client.delete_preset(name)
            self.app.notify(f"Preset '{name}' deleted", severity="information", timeout=3)
            if self._selected >= len(self._presets) - 1:
                self._selected = max(0, len(self._presets) - 2)
            await self._load_presets()
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=5)
