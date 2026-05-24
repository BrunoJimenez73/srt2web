"""
Locust load tests for SRT2Web API.

Scenarios:
1. DashboardMonitoring - Simulates dashboard client polling status/config
2. PipelineControl - Simulates start/stop pipeline operations
3. MixedLoad - Combines monitoring and control operations

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:9999
    locust -f tests/load/locustfile.py --host=http://localhost:9999 --headless -u 10 -r 2 --run-time 60s
"""

import time
from random import randint

from locust import HttpUser, between, task


class DashboardMonitoring(HttpUser):
    """
    Simula un cliente dashboard que hace polling de status y config.
    Escenario típico: 1 request cada 3-5 segundos.
    """

    wait_time = between(3, 5)

    @task(5)
    def get_status(self) -> None:
        """Poll pipeline status (endpoint más usado)."""
        with self.client.get("/api/status", name="GET /api/status", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Status returned {resp.status_code}")
            elif resp.elapsed.total_seconds() > 2.0:
                resp.failure(f"Status too slow: {resp.elapsed.total_seconds():.2f}s")

    @task(2)
    def get_config(self) -> None:
        """Get current configuration."""
        with self.client.get("/api/config", name="GET /api/config", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Config returned {resp.status_code}")

    @task(1)
    def health_check(self) -> None:
        """Health endpoint."""
        with self.client.get("/health", name="GET /health", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Health returned {resp.status_code}")

    @task(1)
    def list_outputs(self) -> None:
        """List outputs."""
        with self.client.get("/api/outputs", name="GET /api/outputs", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Outputs returned {resp.status_code}")

    @task(1)
    def list_recordings(self) -> None:
        """List recordings."""
        with self.client.get("/api/recordings", name="GET /api/recordings", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Recordings returned {resp.status_code}")


class PipelineControl(HttpUser):
    """
    Simula un operador que inicia/para el pipeline y cambia config.
    Más agresivo: operaciones de escritura.
    """

    wait_time = between(10, 20)

    def on_start(self) -> None:
        """Ensure pipeline is not running at start."""
        self.client.post("/api/stop", name="POST /api/stop (setup)")

    @task(1)
    def start_stop_pipeline(self) -> None:
        """Start and immediately stop the pipeline."""
        with self.client.post("/api/start", name="POST /api/start", catch_response=True) as resp:
            if resp.status_code == 400:
                resp.success()  # Already running is OK
            elif resp.status_code != 200:
                resp.failure(f"Start returned {resp.status_code}")

        time.sleep(1)

        with self.client.post("/api/stop", name="POST /api/stop", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"Stop returned {resp.status_code}")

    @task(2)
    def update_chunk_duration(self) -> None:
        """Change chunk duration (common operation)."""
        duration = randint(2, 10)
        with self.client.post(
            "/api/config/chunk",
            json={"chunk_duration_sec": duration},
            name="POST /api/config/chunk",
            catch_response=True,
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"Chunk update returned {resp.status_code}")

    @task(1)
    def toggle_module(self) -> None:
        """Toggle a module on/off."""
        modules = ["translator", "tts_engine"]
        for module in modules:
            with self.client.put(
                f"/api/modules/{module}/toggle",
                json={"enabled": False},
                name="PUT /api/modules/{name}/toggle",
                catch_response=True,
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"Toggle returned {resp.status_code}")

    @task(1)
    def apply_preset(self) -> None:
        """Apply a built-in preset."""
        with self.client.post(
            "/api/presets/low_latency/apply",
            name="POST /api/presets/{name}/apply",
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 404):
                resp.failure(f"Preset returned {resp.status_code}")


class MixedLoad(HttpUser):
    """
    Combina monitoreo y control para simular uso real mixto.
    Representa ~70% lecturas, ~30% escrituras.
    """

    wait_time = between(2, 6)

    @task(7)
    def read_operations(self) -> None:
        """Mix of read endpoints."""
        import random

        endpoint = random.choice(
            [
                "/api/status",
                "/api/config",
                "/api/health",
                "/api/outputs",
                "/api/presets",
            ]
        )
        with self.client.get(endpoint, name=f"GET {endpoint}", catch_response=True) as resp:
            if resp.status_code != 200:
                resp.failure(f"{endpoint} returned {resp.status_code}")

    @task(3)
    def write_operations(self) -> None:
        """Mix of write endpoints."""
        import random

        action = random.choice(["chunk", "toggle", "preset"])
        if action == "chunk":
            with self.client.post(
                "/api/config/chunk",
                json={"chunk_duration_sec": randint(2, 10)},
                name="POST /api/config/chunk",
                catch_response=True,
            ) as resp:
                if resp.status_code != 200:
                    resp.failure(f"Chunk returned {resp.status_code}")
        elif action == "toggle":
            with self.client.put(
                "/api/modules/translator/toggle",
                json={"enabled": False},
                name="PUT /api/modules/toggle",
                catch_response=True,
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"Toggle returned {resp.status_code}")
        elif action == "preset":
            with self.client.post(
                "/api/presets/low_latency/apply",
                name="POST /api/presets/apply",
                catch_response=True,
            ) as resp:
                if resp.status_code not in (200, 404):
                    resp.failure(f"Preset returned {resp.status_code}")
