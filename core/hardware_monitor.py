import psutil
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("srt2web.hardware_monitor")

class HardwareMonitor:
    """
    Clase especializada en el monitoreo de recursos de hardware (CPU, RAM, GPU).
    Centraliza la lógica de recolección de métricas para evitar redundancia en el pipeline.
    """
    def __init__(self):
        self._nvml_initialized = False
        try:
            import pynvml  # type: ignore[import-untyped]
            self._pynvml = pynvml
        except ImportError:
            self._pynvml = None
            logger.warning("pynvml not installed, GPU monitoring will be disabled")

    def _init_nvml(self):
        """Inicializa NVML si está disponible y no ha sido inicializado."""
        if self._pynvml and not self._nvml_initialized:
            try:
                self._pynvml.nvmlInit()
                self._nvml_initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize NVML: {e}")
                self._pynvml = None

    def get_system_metrics(self) -> Dict[str, Any]:
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
            "gpu_available": False
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

        return metrics

    def shutdown(self):
        """Cierra la sesión de NVML si estaba activa."""
        if self._nvml_initialized and self._pynvml:
            try:
                self._pynvml.nvmlShutdown()
            except Exception as e:
                logger.error(f"Error shutting down NVML: {e}")
            finally:
                self._nvml_initialized = False