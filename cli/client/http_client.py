from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import httpx


@dataclass
class PipelineStatus:
    state: str = ""
    mode: str = ""
    chunks_processed: int = 0
    chunks_failed: int = 0
    avg_processing_time_ms: float = 0.0
    uptime_seconds: float = 0.0
    max_concurrent_chunks: int = 3
    concurrent_chunks: int = 0
    buffer_size: int = 5
    modules: list[dict] = field(default_factory=list)
    system: dict = field(default_factory=dict)
    system_metrics: dict = field(default_factory=dict)
    strategy: str = ""
    network: dict | None = None
    sync: dict | None = None
    input_receiving: bool = False
    input_info: dict | None = None

    @classmethod
    def from_dict(cls, data: dict) -> PipelineStatus:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ConfigData:
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> ConfigData:
        return cls(raw=data)

    def get(self, dotted_key: str) -> Any:
        parts = dotted_key.split(".")
        val = self.raw
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return None
        return val

    def set(self, dotted_key: str, value: Any) -> None:
        parts = dotted_key.split(".")
        target = self.raw
        for p in parts[:-1]:
            target = target.setdefault(p, {})
        target[parts[-1]] = value


@dataclass
class OutputInfo:
    name: str = ""
    type: str = ""
    state: str = "idle"
    enabled: bool = True
    processed_chunks: int = 0
    last_process_time_ms: float = 0.0
    stream_info: dict | None = None
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> OutputInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class ModuleInfo:
    name: str = ""
    state: str = "idle"
    enabled: bool = True
    processed_chunks: int = 0
    last_process_time_ms: float = 0.0
    circuit_state: str = "closed"
    memory_mb: float = 0.0
    extra: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> ModuleInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class NetworkInfo:
    server_ip: str = ""
    server_port: int = 9999
    stream_url: str = ""
    player_url: str = ""
    srt_url_listener: str | None = None
    srt_url_caller_template: str | None = None
    latency_ms: int = 0
    srt_mode: str = ""
    local_ip: str = ""
    public_ip: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> NetworkInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class HealthInfo:
    status: str = "ok"
    uptime_seconds: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0
    chunks_processed: int = 0
    pipeline_state: str = "stopped"
    modules: list[dict] = field(default_factory=list)
    input: dict = field(default_factory=dict)
    output: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> HealthInfo:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class LogEntry:
    level: str = "INFO"
    message: str = ""
    timestamp: float = 0.0
    logger: str = "root"

    @property
    def time_str(self) -> str:
        if not self.timestamp:
            return ""
        return datetime.fromtimestamp(self.timestamp).strftime("%H:%M:%S")

    @classmethod
    def from_dict(cls, data: dict) -> LogEntry:
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


DEFAULT_SERVER = "http://localhost:9999"


class APIClient:
    def __init__(self, base_url: str = DEFAULT_SERVER, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(15.0, connect=5.0),
            headers=self._headers(),
        )

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str) -> Any:
        r = await self._client.get(path)
        if r.status_code == 401:
            raise PermissionError("Authentication required. Use --token or login first.")
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, data: dict | None = None, timeout: float = 15.0) -> Any:
        r = await self._client.post(path, json=data or {}, timeout=httpx.Timeout(timeout, connect=5.0))
        if r.status_code == 401:
            raise PermissionError("Authentication required.")
        r.raise_for_status()
        return r.json()

    async def _put(self, path: str, data: dict | None = None) -> Any:
        r = await self._client.put(path, json=data or {})
        if r.status_code == 401:
            raise PermissionError("Authentication required.")
        r.raise_for_status()
        return r.json()

    async def _delete(self, path: str) -> Any:
        r = await self._client.delete(path)
        if r.status_code == 401:
            raise PermissionError("Authentication required.")
        r.raise_for_status()
        return r.json()

    async def get_status(self) -> PipelineStatus:
        data = await self._get("/api/status")
        return PipelineStatus.from_dict(data)

    async def get_health(self) -> HealthInfo:
        data = await self._get("/api/health")
        return HealthInfo.from_dict(data)

    async def start_pipeline(self) -> dict:
        return await self._post("/api/start", timeout=30.0)

    async def stop_pipeline(self) -> dict:
        return await self._post("/api/stop", timeout=30.0)

    async def restart_pipeline(self) -> dict:
        return await self._post("/api/restart", timeout=30.0)

    async def get_config(self) -> ConfigData:
        data = await self._get("/api/config")
        return ConfigData.from_dict(data)

    async def update_config(self, config: dict) -> dict:
        return await self._put("/api/config", {"config": config})

    async def update_chunk(self, chunk_duration_sec: int) -> dict:
        return await self._post("/api/config/chunk", {"chunk_duration_sec": chunk_duration_sec})

    async def get_modules(self) -> list[ModuleInfo]:
        data = await self._get("/api/modules")
        return [ModuleInfo.from_dict(m) for m in data.get("modules", [])]

    async def toggle_module(self, name: str, enabled: bool) -> dict:
        return await self._put(f"/api/modules/{name}/toggle", {"enabled": enabled})

    async def get_module_debug(self, name: str) -> dict:
        return await self._get(f"/api/modules/{name}/debug")

    async def get_outputs(self) -> list[OutputInfo]:
        data = await self._get("/api/outputs")
        return [OutputInfo.from_dict(o) for o in data.get("outputs", [])]

    async def get_available_outputs(self) -> list[str]:
        data = await self._get("/api/outputs/available")
        return data.get("available_types", [])

    async def add_output(self, output_type: str, name: str | None = None, config: dict | None = None) -> dict:
        body = {"type": output_type}
        if name:
            body["name"] = name
        if config:
            body["config"] = config
        return await self._post("/api/outputs", body)

    async def remove_output(self, name: str) -> dict:
        return await self._delete(f"/api/outputs/{name}")

    async def toggle_output(self, name: str, enabled: bool | None = None) -> dict:
        body = {}
        if enabled is not None:
            body["enabled"] = enabled
        return await self._post(f"/api/outputs/{name}/toggle", body)

    async def get_input_info(self) -> dict:
        return await self._get("/api/input-info")

    async def control_input(self, action: str, data: dict | None = None) -> dict:
        return await self._post(f"/api/input/control/{action}", data)

    async def get_network_info(self) -> NetworkInfo:
        data = await self._get("/api/network/info")
        return NetworkInfo.from_dict(data)

    async def get_available(self) -> dict:
        return await self._get("/api/available")

    async def get_presets(self) -> list:
        data = await self._get("/api/presets")
        return data.get("presets", [])

    async def save_preset(self, name: str, description: str = "") -> dict:
        return await self._post("/api/presets", {"name": name, "description": description})

    async def apply_preset(self, name: str) -> dict:
        return await self._post(f"/api/presets/{name}/apply")

    async def delete_preset(self, name: str) -> dict:
        return await self._delete(f"/api/presets/{name}")

    async def login(self, username: str, password: str) -> str:
        data = await self._post("/api/auth/login", {"username": username, "password": password})
        self.token = data.get("token", "")
        self._client.headers.update(self._headers())
        return self.token

    async def get_recordings(self) -> list:
        data = await self._get("/api/recordings")
        return data.get("recordings", [])

    async def delete_recording(self, name: str) -> dict:
        return await self._delete(f"/api/recordings/{name}")

    async def health_check(self) -> dict:
        return await self._get("/health")
