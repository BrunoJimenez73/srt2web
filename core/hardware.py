"""
Hardware Auto-Detection - Sugerencia 2 de Auditoría.

Sistema de "Perfiles de Hardware" que detecta automáticamente si debe usar:
- CUDA (NVIDIA)
- MPS (Mac Silicon)
- CPU (fallback)

Elimina la necesidad de que el usuario edite el config.yaml manualmente.
"""

import logging
import sys
from enum import Enum
from typing import Any

logger = logging.getLogger("srt2web.hardware")


class HardwareType(str, Enum):
    """Tipos de hardware disponibles."""

    CPU = "cpu"
    CUDA = "cuda"
    MPS = "mps"


def detect_cuda() -> dict[str, Any]:
    """
    Detecta si CUDA (NVIDIA) está disponible y funcional.

    Returns:
        Dict con: available (bool), device_count, devices (list), error (str)
    """
    result: dict[str, Any] = {
        "available": False,
        "device_count": 0,
        "devices": [],
        "error": None,
    }

    try:
        import torch

        cuda_available = torch.cuda.is_available()
        if not isinstance(cuda_available, bool):
            result["error"] = "torch.cuda.is_available() returned non-bool value"
            return result

        if cuda_available:
            result["available"] = True
            device_count = torch.cuda.device_count()
            result["device_count"] = device_count if isinstance(device_count, int) else 0
            for i in range(result["device_count"]):
                try:
                    props = torch.cuda.get_device_properties(i)
                    total_mem = getattr(props, "total_mem", getattr(props, "total_memory", 0))
                    result["devices"].append(
                        {
                            "index": i,
                            "name": props.name,
                            "total_memory_mb": total_mem / (1024**2) if total_mem else 0,
                            "compute_capability": f"{props.major}.{props.minor}",
                        }
                    )
                except Exception as e:
                    logger.debug(f"Could not get GPU {i} properties: {e}")

            # Verificar que podemos crear un tensor en CUDA
            try:
                test_tensor = torch.tensor([1.0]).cuda()
                test_tensor.cpu()  # Cleanup
                logger.info(f"CUDA detection: {result['device_count']} device(s) available")
            except Exception as e:
                result["available"] = False
                result["error"] = f"CUDA available but tensor creation failed: {e}"
                logger.warning(f"CUDA tensor creation test failed: {e}")
        else:
            result["error"] = "torch.cuda.is_available() returned False"
            logger.debug("CUDA not available via PyTorch")

    except ImportError:
        result["error"] = "PyTorch not installed"
        logger.debug("PyTorch not installed, cannot detect CUDA via torch")

    # Fallback: verificar vía nvidia-smi o pynvml
    if not result["available"]:
        try:
            import pynvml

            pynvml.nvmlInit()
            device_count = pynvml.nvmlDeviceGetCount()
            result["available"] = device_count > 0
            result["device_count"] = device_count
            for i in range(device_count):
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle)
                    # Handle both bytes (old pynvml) and str (new pynvml)
                    if isinstance(name, bytes):
                        name = name.decode("utf-8")
                    result["devices"].append(
                        {
                            "index": i,
                            "name": name,
                            "total_memory_mb": None,  # Need to get memory info
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error getting NVML info for GPU {i}: {e}")
            logger.info(f"CUDA detection via NVML: {device_count} device(s) available")
        except ImportError:
            pass  # NVML not available
        except Exception as e:
            logger.debug(f"NVML detection failed: {e}")

    return result


def detect_mps() -> dict[str, Any]:
    """
    Detecta si MPS (Mac Silicon) está disponible.

    Returns:
        Dict con: available (bool), error (str)
    """
    result: dict[str, Any] = {
        "available": False,
        "error": None,
    }

    # MPS solo está disponible en macOS y Python 3.8+
    if sys.platform != "darwin":
        result["error"] = "MPS only available on macOS"
        return result

    try:
        import torch

        if hasattr(torch, "backends") and hasattr(torch.backends, "mps"):
            if torch.backends.mps.is_available():
                result["available"] = True
                logger.info("MPS (Mac Silicon) detection: available")

                # Verificar que podemos usar MPS
                try:
                    test_tensor = torch.tensor([1.0]).to("mps")
                    test_tensor.cpu()  # Cleanup
                except Exception as e:
                    result["available"] = False
                    result["error"] = f"MPS available but tensor creation failed: {e}"
                    logger.warning(f"MPS tensor creation test failed: {e}")
            else:
                result["error"] = "torch.backends.mps.is_available() returned False"
                logger.debug("MPS not available via PyTorch")
        else:
            result["error"] = "PyTorch version does not support MPS"
            logger.debug("PyTorch does not support MPS")

    except ImportError:
        result["error"] = "PyTorch not installed"
        logger.debug("PyTorch not installed, cannot detect MPS")

    return result


def detect_hardware() -> dict[str, Any]:
    """
    Detecta todo el hardware disponible en el sistema.

    Returns:
        Dict con: cuda (dict), mps (dict), cpu_always (True), recommended (str)
    """
    cuda_info = detect_cuda()
    mps_info = detect_mps()

    # Determinar el dispositivo recomendado
    recommended = "cpu"  # fallback por defecto

    if cuda_info["available"]:
        recommended = "cuda"
    elif mps_info["available"]:
        recommended = "mps"

    return {
        "cuda": cuda_info,
        "mps": mps_info,
        "cpu_always": True,
        "recommended": recommended,
    }


def get_optimal_device(preferred: str | None = None) -> str:
    """
    Obtiene el mejor dispositivo para usar.

    Args:
        preferred: Dispositivo preferido ("cuda", "mps", "cpu", "auto")
                   Si es "auto" o None, detecta automáticamente.

    Returns:
        str: "cuda", "mps", o "cpu"
    """
    if preferred is None or preferred == "auto":
        hardware = detect_hardware()
        return str(hardware["recommended"])

    if preferred == "cuda":
        cuda_info = detect_cuda()
        if cuda_info["available"]:
            return "cuda"
        else:
            logger.warning(f"CUDA requested but not available: {cuda_info.get('error')}")
            return "cpu"

    if preferred == "mps":
        mps_info = detect_mps()
        if mps_info["available"]:
            return "mps"
        else:
            logger.warning(f"MPS requested but not available: {mps_info.get('error')}")
            return "cpu"

    return "cpu"  # fallback


def update_config_with_optimal_device(config: dict[str, Any]) -> dict[str, Any]:
    """
    Actualiza la configuración con el dispositivo óptimo detectado automáticamente.

    Args:
        config: Configuración actual del sistema

    Returns:
        Configuración actualizada con los dispositivos óptimos
    """
    hardware = detect_hardware()
    optimal_device = hardware["recommended"]

    # Actualizar configuración de módulos que usan dispositivos
    modules_to_update = ["transcriber", "tts_engine"]

    # F117 fix: config dict has modules nested under "modules" key
    modules_section = config.get("modules", config)

    for module_name in modules_to_update:
        if module_name in modules_section:
            current_device = modules_section[module_name].get("device", "auto")

            # Solo actualizar si está en "auto" o si el dispositivo actual no está disponible
            if current_device == "auto":
                modules_section[module_name]["device"] = optimal_device
                logger.info(f"Auto-set {module_name} device to: {optimal_device}")
            elif current_device != optimal_device:
                # Verificar si el dispositivo actual está disponible
                if current_device == "cuda" and not hardware["cuda"]["available"]:
                    modules_section[module_name]["device"] = optimal_device
                    logger.warning(f"CUDA not available for {module_name}, switching to: {optimal_device}")
                elif current_device == "mps" and not hardware["mps"]["available"]:
                    modules_section[module_name]["device"] = optimal_device
                    logger.warning(f"MPS not available for {module_name}, switching to: {optimal_device}")

    return config


# Exportar para facilitar importación
__all__ = [
    "HardwareType",
    "detect_cuda",
    "detect_hardware",
    "detect_mps",
    "get_optimal_device",
    "update_config_with_optimal_device",
]
