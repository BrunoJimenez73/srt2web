import logging
import sys
from typing import Any

import psutil

logger = logging.getLogger("srt2web.hardware_monitor")


class HardwareMonitor:
    """
    Clase especializada en el monitoreo de recursos de hardware (CPU, RAM, GPU).
    Centraliza la lógica de recolección de métricas para evitar redundancia en el pipeline.

    Soporta:
    - NVIDIA GPU via pynvml (Windows/Linux)
    - Apple Silicon GPU via sysctl (macOS, cuando no hay pynvml)
    - CPU/RAM via psutil (todas las plataformas)
    """

    def __init__(self) -> None:
        self._nvml_initialized = False
        self._is_macos = sys.platform == "darwin"
        try:
            import pynvml  # type: ignore[import-untyped]

            self._pynvml = pynvml
        except ImportError:
            self._pynvml = None
            if not self._is_macos:
                logger.warning("pynvml not installed, GPU monitoring disabled")
            else:
                logger.info("macOS detected: using sysctl for Apple Silicon metrics")

    def _init_nvml(self) -> None:
        """Inicializa NVML si está disponible y no ha sido inicializado."""
        if self._pynvml and not self._nvml_initialized:
            try:
                self._pynvml.nvmlInit()
                self._nvml_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize NVML: {e}")
                self._pynvml = None

    def _get_macos_gpu_metrics(self) -> dict[str, Any]:
        """
        Obtiene métricas de GPU en macOS Apple Silicon usando sysctl.

        Returns:
            Dict with gpu_usage (estimated) and gpu_available flag.
            Apple Silicon no expone % de uso GPU fácilmente,
            así que se estima desde sysctl y métricas de proceso.
        """
        import subprocess

        metrics: dict[str, Any] = {
            "gpu_usage": 0.0,
            "gpu_percent": 0.0,
            "gpu_memory_mb": 0.0,
            "gpu_memory_usage": 0.0,
            "gpu_available": True,
        }

        try:
            # Apple Silicon reports GPU utilization via sysctl
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.thermal_level"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                # thermal_level is 0-4, where 0=idle, 4=critical
                thermal = int(result.stdout.strip())
                metrics["gpu_usage"] = thermal * 25.0
                metrics["gpu_percent"] = min(thermal * 25.0, 100.0)

            # Try powermetrics for actual GPU usage (requires root)
            # Fallback: use CPU load as rough proxy
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if metrics["gpu_usage"] == 0.0:
                metrics["gpu_usage"] = cpu_percent * 0.5
                metrics["gpu_percent"] = metrics["gpu_usage"]
        except Exception:
            metrics["gpu_usage"] = 0.0
            metrics["gpu_percent"] = 0.0

        return metrics

    def get_system_metrics(self) -> dict[str, Any]:
        """
        Recopila métricas actuales del sistema.
        Retorna un diccionario con CPU, RAM y GPU (si está disponible).
        """
        metrics = {
            "cpu_usage": 0.0,
            "cpu_percent": 0.0,
            "memory_usage": 0.0,
            "memory_percent": 0.0,
            "memory_mb": 0.0,
            "gpu_usage": 0.0,
            "gpu_percent": 0.0,
            "gpu_memory_usage": 0.0,
            "gpu_memory_mb": 0.0,
            "gpu_available": False,
        }

        # Métricas de CPU y RAM
        try:
            cpu_percent = psutil.cpu_percent()
            mem = psutil.virtual_memory()

            metrics["cpu_usage"] = cpu_percent
            metrics["cpu_percent"] = cpu_percent
            metrics["memory_usage"] = mem.percent
            metrics["memory_percent"] = mem.percent
            metrics["memory_mb"] = mem.used / (1024 * 1024)
        except Exception as e:
            logger.debug(f"Error collecting CPU/RAM metrics: {e}")

        # Métricas de GPU (NVIDIA)
        if self._pynvml:
            try:
                self._init_nvml()
                if self._pynvml:
                    handle = self._pynvml.nvmlDeviceGetHandleByIndex(0)
                    util = self._pynvml.nvmlDeviceGetUtilizationRates(handle)
                    mem_gpu = self._pynvml.nvmlDeviceGetMemoryInfo(handle)

                    gpu_percent = util.gpu
                    gpu_memory_mb = mem_gpu.used / (1024 * 1024)

                    metrics["gpu_usage"] = gpu_percent
                    metrics["gpu_percent"] = gpu_percent
                    metrics["gpu_memory_usage"] = int(mem_gpu.used / mem_gpu.total * 100)
                    metrics["gpu_memory_mb"] = gpu_memory_mb
                    metrics["gpu_available"] = True
            except Exception as e:
                logger.debug(f"Error collecting GPU metrics: {e}")
        elif self._is_macos:
            macos_metrics = self._get_macos_gpu_metrics()
            metrics.update(macos_metrics)

        return metrics

    def shutdown(self) -> None:
        """Cierra la sesión de NVML si estaba activa."""
        if self._nvml_initialized and self._pynvml:
            try:
                self._pynvml.nvmlShutdown()
            except Exception as e:
                logger.error(f"Error shutting down NVML: {e}")
            finally:
                self._nvml_initialized = False
