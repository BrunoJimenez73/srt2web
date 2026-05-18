from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import Static

CARD_NAMES = [
    "input",
    "audio_extractor",
    "transcriber",
    "translator",
    "subtitle_generator",
    "tts_engine",
    "audio_mixer",
    "video_muxer",
]


class TUIModuleCard(Static, can_focus=True):
    def __init__(self, module_name: str, id: str | None = None):
        super().__init__(id=id)
        self.module_name = module_name
        self._state = "idle"
        self._enabled = True
        self._chunks = 0
        self._last_time = 0.0
        self._extra: dict[str, Any] = {}
        self._memory_mb = 0.0

    def on_mount(self) -> None:
        self._render_card()

    def update(
        self, state: str, enabled: bool, chunks: int, last_time: float, extra: dict[str, Any] | None = None
    ) -> None:  # type: ignore[override]
        self._state = state
        self._enabled = enabled
        self._chunks = chunks
        self._last_time = last_time
        self._extra = extra or {}
        if extra:
            self._memory_mb = extra.get("memory_mb", 0.0) or 0.0
        self._render_card()

    def on_click(self) -> None:
        self.post_message(CardClicked(self.module_name))

    def _render_card(self) -> None:
        state_style = {
            "running": "green",
            "processing": "green",
            "starting": "yellow",
            "initializing": "blue",
            "stopping": "yellow",
            "stopped": "dim white",
            "idle": "dim white",
            "error": "red",
            "degraded": "orange1",
            "disabled": "dim",
        }.get(self._state, "white")

        if not self._enabled:
            state_dot = Text("—", style="dim")
        elif self._state in ("running", "processing"):
            state_dot = Text("●", style=f"bold {state_style}")
        elif self._state in ("error",):
            state_dot = Text("✖", style=f"bold {state_style}")
        elif self._state in ("degraded",):
            state_dot = Text("⚠", style=f"bold {state_style}")
        else:
            state_dot = Text("●", style=state_style)

        label = self.module_name.replace("_", " ").title()

        using_gpu = self._extra.get("using_gpu", False)
        gpu_text = " [GPU]" if using_gpu else ""

        mem_str = f" {self._memory_mb:.0f}MB" if self._memory_mb else ""

        t = Text.assemble(
            state_dot,
            (" ", ""),
            (f"{label}", "bold"),
            "\n",
            (f"  {self._state}", state_style),
            gpu_text,
            "\n",
            (f"  {self._chunks}ch | {self._last_time:.0f}ms |{mem_str}", "dim"),
        )
        super().update(t)


class CardClicked(Message):
    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name


class TUIModuleGrid(Static):
    BINDINGS = [
        ("right", "move_next", "Next"),
        ("down", "move_next", "Next"),
        ("left", "move_prev", "Prev"),
        ("up", "move_prev", "Prev"),
        ("enter", "select_card", "Open"),
    ]

    def compose(self) -> ComposeResult:
        from textual.containers import Horizontal, Vertical

        with Vertical():
            with Horizontal():
                for name in CARD_NAMES[:4]:
                    yield TUIModuleCard(name, id=f"card-{name}")
            with Horizontal():
                for name in CARD_NAMES[4:]:
                    yield TUIModuleCard(name, id=f"card-{name}")

    def update_modules(self, modules: list[dict[str, Any]]) -> None:
        cards = {card.module_name: card for card in self.query(TUIModuleCard)}
        module_info_map = {m.get("name", ""): m for m in modules}

        for name, card in cards.items():
            mod = module_info_map.get(name, {})
            state = mod.get("state", "idle")
            enabled = mod.get("enabled", True)
            chunks = mod.get("processed_chunks", 0)
            last_time = mod.get("last_process_time_ms", 0.0)
            extra = mod.get("extra", {})
            card.update(state, enabled, chunks, last_time, extra)

        for mod in modules:
            name = mod.get("name", "")
            if name == "output" and "video_muxer" in cards:
                state = mod.get("state", "idle")
                enabled = mod.get("enabled", True)
                chunks = mod.get("processed_chunks", 0)
                last_time = mod.get("last_process_time_ms", 0.0)
                extra = mod.get("extra", {})
                cards["video_muxer"].update(state, enabled, chunks, last_time, extra)

    def on_card_clicked(self, event: CardClicked) -> None:
        self._selected_index = CARD_NAMES.index(event.module_name) if event.module_name in CARD_NAMES else 0
        self.post_message(ModuleSelected(event.module_name))

    def move_selection(self, delta: int) -> None:
        self._selected_index = (self._selected_index + delta) % len(CARD_NAMES)
        cards = list(self.query(TUIModuleCard))
        if 0 <= self._selected_index < len(cards):
            cards[self._selected_index].focus()

    def focus_card(self, index: int) -> None:
        self._selected_index = index % len(CARD_NAMES)
        cards = list(self.query(TUIModuleCard))
        if 0 <= self._selected_index < len(cards):
            cards[self._selected_index].focus()

    def action_move_next(self) -> None:
        self.move_selection(1)

    def action_move_prev(self) -> None:
        self.move_selection(-1)

    def action_select_card(self) -> None:
        if 0 <= self._selected_index < len(CARD_NAMES):
            self.post_message(ModuleSelected(CARD_NAMES[self._selected_index]))


class ModuleSelected(Message):
    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name
