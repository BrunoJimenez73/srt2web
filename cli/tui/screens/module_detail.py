from __future__ import annotations

import logging
from typing import Any

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static, Switch

from cli.client.http_client import ModuleInfo

logger = logging.getLogger(__name__)

MODULE_CONFIG_SCHEMA: dict[str, list[tuple[str, str, type, tuple[Any, ...]]]] = {
    "input": [
        ("Type", "type", str, ("srt", "rtmp", "file")),
        ("SRT Port", "srt_listen_port", int, ()),
        ("SRT Mode", "srt_mode", str, ("listener", "caller", "rendezvous")),
        ("SRT Latency (ms)", "srt_latency_ms", int, ()),
        ("Chunk Duration (s)", "chunk_duration_sec", int, ()),
    ],
    "audio_extractor": [
        ("Enabled", "enabled", bool, ()),
    ],
    "transcriber": [
        ("Enabled", "enabled", bool, ()),
        ("Model", "model", str, ("tiny", "small", "medium", "large-v2")),
        ("Language", "language", str, ("auto", "es", "en", "fr", "de", "it", "pt")),
        ("Device", "device", str, ("auto", "cuda", "cpu")),
    ],
    "translator": [
        ("Enabled", "enabled", bool, ()),
        ("Source Lang", "source_lang", str, ("auto", "es", "en", "fr", "de", "it", "pt")),
        ("Target Lang", "target_lang", str, ("es", "en", "fr", "de", "it", "pt")),
    ],
    "subtitle_generator": [
        ("Enabled", "enabled", bool, ()),
        ("Format", "format", str, ("webvtt", "srt")),
        ("Use Translated", "use_translated", bool, ()),
    ],
    "tts_engine": [
        ("Enabled", "enabled", bool, ()),
        ("Engine", "engine", str, ("edge-tts", "piper")),
        (
            "Voice",
            "voice",
            str,
            ("es-ES-AlvaroNeural", "es-ES-ElviraNeural", "es_ES-sharvard-medium", "es_MX-claude-high"),
        ),
        ("Speed", "speed", float, ()),
        ("Device", "device", str, ("auto", "cuda", "cpu")),
    ],
    "audio_mixer": [
        ("Enabled", "enabled", bool, ()),
        ("Original Volume", "original_volume", float, ()),
        ("TTS Volume", "tts_volume", float, ()),
    ],
    "video_muxer": [
        ("Enabled", "enabled", bool, ()),
        ("Engine", "engine", str, ("hls", "webrtc")),
        ("Encoder Mode", "encoder_mode", str, ("auto", "passthrough", "cpu", "gpu_nvenc")),
        ("CRF", "video_crf", int, ()),
        ("Audio Offset (ms)", "audio_offset_ms", int, ()),
        ("Audio Codec", "audio_codec", str, ("aac", "opus")),
        ("Audio Bitrate", "audio_bitrate", str, ("64k", "96k", "128k", "192k", "256k", "320k")),
        ("Video FPS", "video_fps", int, ()),
    ],
}

MODULE_TITLES: dict[str, str] = {
    "input": "INPUT",
    "audio_extractor": "AUDIO EXTRACTOR",
    "transcriber": "WHISPER",
    "translator": "TRANSLATOR",
    "subtitle_generator": "SUBTITLE",
    "tts_engine": "TTS",
    "audio_mixer": "AUDIO MIXER",
    "video_muxer": "VIDEO MUXER",
}

MODULE_ICONS: dict[str, str] = {
    "input": "[INPUT]",
    "audio_extractor": "[AUDIO]",
    "transcriber": "[WHISPER]",
    "translator": "[TRANSL]",
    "subtitle_generator": "[SUBTIT]",
    "tts_engine": "[TTS]",
    "audio_mixer": "[MIXER]",
    "video_muxer": "[MUXER]",
}


class ConfigField(Vertical):
    def __init__(self, label: str, key: str, field_type: type, options: tuple[Any, ...], value: str = ""):
        super().__init__(classes="config-field")
        self.label = label
        self.key = key
        self.field_type = field_type
        self.options = options
        self._initial_value = value

    def compose(self) -> ComposeResult:
        yield Static(f"{self.label}:", classes="field-label")
        if self.field_type == bool:
            yield Switch(value=self._initial_value == "True", id=f"sw-{self.key}")
        elif self.options:
            current = self._initial_value if self._initial_value else self.options[0]
            select_options = [(opt, opt) for opt in self.options]
            yield Select(options=select_options, value=current, id=f"sel-{self.key}")
        else:
            yield Input(value=self._initial_value or "", id=f"in-{self.key}")


class ModuleConfigForm(Vertical):
    def __init__(self, module_name: str, module_info: ModuleInfo | None, config: dict[str, Any]):
        super().__init__(classes="module-config-form")
        self.module_name = module_name
        self.module_info = module_info
        self.config = config or {}
        self.module_config = self.config.get("modules", {}).get(module_name, {})

    def compose(self) -> ComposeResult:
        schema = MODULE_CONFIG_SCHEMA.get(self.module_name, [])

        state = "idle"
        enabled = True
        chunks = 0
        last_time = 0.0
        if self.module_info:
            state = self.module_info.state
            enabled = self.module_info.enabled
            chunks = self.module_info.processed_chunks
            last_time = self.module_info.last_process_time_ms

        state_color = {
            "running": "green",
            "processing": "green",
            "starting": "yellow",
            "idle": "dim white",
            "stopped": "dim",
            "error": "red",
        }.get(state, "white")

        title = MODULE_TITLES.get(self.module_name, self.module_name.upper())
        icon = MODULE_ICONS.get(self.module_name, "[" + self.module_name.upper()[:7] + "]")

        yield Static(f"{icon} {title}", classes="form-title")
        yield Static(
            f"State: {state} | Chunks: {chunks} | Time: {last_time:.0f}ms", id="form-status-line", classes="form-status"
        )

        if schema:
            yield Static("Configuration:", classes="section-label")
            for label, key, field_type, options in schema:
                raw_val = self._get_nested(key, self.module_config)
                str_val = str(raw_val) if raw_val is not None else ""
                yield ConfigField(label, key, field_type, options, str_val)

        yield Static("Metrics:", classes="section-label")
        mem_mb = self.module_info.memory_mb if self.module_info else 0.0
        circuit = getattr(self.module_info, "circuit_state", "closed") if self.module_info else "closed"
        extra_info = self.module_info.extra if self.module_info else {}
        gpu_info = extra_info.get("using_gpu", False) or extra_info.get("device", "")
        yield Static(
            f"Memory: {mem_mb:.0f} MB | Circuit: {circuit} | GPU: {gpu_info or 'N/A'}",
            id="form-metrics-line",
            classes="form-metrics",
        )

        yield Horizontal(
            Button("Save", variant="primary", id="btn-save-module"),
            Button("Toggle Enable", id="btn-toggle-module"),
            Button("Back", variant="default", id="btn-back-module"),
            classes="form-buttons",
        )

    def _get_nested(self, key: str, data: dict[str, Any]) -> str | None:
        if key in data:
            return str(data[key])
        return None

    @on(Button.Pressed, "#btn-save-module")
    def on_save(self) -> None:
        self.post_message(ModuleConfigSaved(self.module_name, self._collect_values()))

    @on(Button.Pressed, "#btn-toggle-module")
    def on_toggle(self) -> None:
        self.post_message(ModuleToggleRequest(self.module_name))

    @on(Button.Pressed, "#btn-back-module")
    def on_back(self) -> None:
        self.post_message(ModuleDetailBack())

    def _collect_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for child in self.query(ConfigField):
            key = child.key
            if child.field_type == bool:
                sw = self.query_one(f"#sw-{key}", Switch)
                values[key] = sw.value
            elif child.options:
                sel = self.query_one(f"#sel-{key}", Select)
                values[key] = sel.value
            else:
                inp = self.query_one(f"#in-{key}", Input)
                try:
                    if child.field_type == int:
                        values[key] = int(inp.value)
                    elif child.field_type == float:
                        values[key] = float(inp.value)
                    else:
                        values[key] = inp.value
                except ValueError:
                    values[key] = inp.value
        return values

    def update_module_info(self, module_dict: dict[str, Any]) -> None:
        state = module_dict.get("state", "idle")
        chunks = module_dict.get("processed_chunks", 0)
        last_time = module_dict.get("last_process_time_ms", 0.0)
        extra = module_dict.get("extra", {})
        mem_mb = extra.get("memory_mb", 0.0) or 0.0
        circuit = module_dict.get("circuit_state", "closed")
        gpu_info = extra.get("using_gpu", False) or extra.get("device", "")
        try:
            status_line = self.query_one("#form-status-line", Static)
            status_line.update(f"State: {state} | Chunks: {chunks} | Time: {last_time:.0f}ms")
            metrics_line = self.query_one("#form-metrics-line", Static)
            metrics_line.update(f"Memory: {mem_mb:.0f} MB | Circuit: {circuit} | GPU: {gpu_info or 'N/A'}")
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)


class ModuleConfigSaved(Message):
    def __init__(self, module_name: str, values: dict[str, Any]):
        super().__init__()
        self.module_name = module_name
        self.values = values


class ModuleToggleRequest(Message):
    def __init__(self, module_name: str):
        super().__init__()
        self.module_name = module_name


class ModuleDetailBack(Message):
    pass


class ModuleDetailScreen(Screen[Any]):
    CSS = """
    Screen.module-detail {
        background: $surface;
    }

    .form-title {
        color: $text;
        text-style: bold;
        margin-bottom: 2;
    }

    .form-status {
        color: $text-muted;
        margin-bottom: 8;
    }

    .section-label {
        color: $accent;
        text-style: bold;
        margin-top: 4;
        margin-bottom: 2;
    }

    .form-metrics {
        color: $text-muted;
        margin-top: 2;
    }

    .module-config-form {
        padding: 4;
    }

    .config-field {
        height: auto;
        margin-top: 2;
    }

    #form-container {
        height: 100%;
        border: solid $primary;
        margin: 1;
    }

    .form-buttons {
        height: 3;
        margin-top: 4;
    }

    .field-label {
        color: $text;
        margin-top: 2;
    }
    """

    BINDINGS = [  # noqa: RUF012
        Binding("escape", "app.pop_screen", "Back"),
    ]

    def __init__(self, module_name: str, module_info: ModuleInfo | None, config: dict[str, Any], api_client: Any):
        super().__init__()
        self.module_name = module_name
        self.module_info = module_info
        self.config = config
        self.api_client = api_client
        self._form_mounted = False
        self._form: ModuleConfigForm | None = None
        self._polling = False
        self._refresh_timer: Any = None

    def compose(self) -> ComposeResult:
        yield ScrollableContainer(id="form-container")

    def on_mount(self) -> None:
        container = self.query_one("#form-container", ScrollableContainer)
        form = ModuleConfigForm(self.module_name, self.module_info, self.config)
        self._form = form
        container.mount(form)
        self._refresh_timer = self.set_interval(2.0, self._poll_module_info)

    async def _poll_module_info(self) -> None:
        if self._polling:
            return
        self._polling = True
        try:
            status = await self.api_client.get_status()
            for m in status.modules:
                if m.get("name") == self.module_name and m.get("state"):
                    if self._form:
                        self._form.update_module_info(m)
                    break
        except Exception as e:
            logger.debug("Suppressed error: %s", e, exc_info=True)
        finally:
            self._polling = False

    def on_unmount(self) -> None:
        if hasattr(self, "_refresh_timer") and self._refresh_timer:
            self._refresh_timer.stop()

    async def on_module_config_saved(self, event: ModuleConfigSaved) -> None:
        if event.module_name in self.config.get("modules", {}):
            self.config["modules"][event.module_name].update(event.values)
            try:
                await self.api_client.update_config(self.config)
                self.app.notify(f"{event.module_name} config saved", severity="information", timeout=3)
            except Exception as e:
                self.app.notify(f"Error: {e}", severity="error", timeout=5)

    async def on_module_toggle_request(self, event: ModuleToggleRequest) -> None:
        try:
            mod = self.module_info
            if mod:
                await self.api_client.toggle_module(event.module_name, not mod.enabled)
                self.app.notify(f"Toggled {event.module_name}", severity="information", timeout=3)
        except Exception as e:
            self.app.notify(f"Error: {e}", severity="error", timeout=5)

    @on(ModuleDetailBack)
    def on_back_event(self) -> None:
        self.app.pop_screen()
