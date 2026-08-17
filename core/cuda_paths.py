"""
CUDA Paths Configuration - Extraído de main.py

Maneja la configuración de paths de CUDA/cuDNN para Windows.
Extraído para mejorar mantenibilidad.

NOTA: En macOS y Linux sin NVIDIA GPU, todas las funciones
retornan listas vacías / hacen no-op automáticamente.
"""

import contextlib
import os
import site
import sys
from pathlib import Path


def get_cuda_paths() -> list[str]:
    """
    Recolecta todos los paths de CUDA/cuDNN disponibles en el sistema.

    Returns:
        Lista de paths priorizados para CUDA (cuDNN 8.x primero).
        Vacía en macOS o sistemas sin CUDA.
    """
    if sys.platform != "win32":
        return []

    cuda_paths: list[str] = []
    from core.paths import get_project_root

    project_root = get_project_root()

    # CRITICAL: Add local cuDNN 8.x FIRST (must be at front to avoid loading cuDNN 9.x)
    local_cudnn8 = project_root / "bin" / "cudnn8"
    if local_cudnn8.exists() and any(local_cudnn8.iterdir()):
        cuda_paths.append(str(local_cudnn8))  # Prioritize cuDNN 8.x

    # Add venv nvidia paths (cuDNN 8.9.4 from pip)
    for sp in site.getsitepackages():
        cudnn_bin = Path(sp) / "nvidia" / "cudnn" / "bin"
        if cudnn_bin.exists():
            cuda_paths.append(str(cudnn_bin))
        cublas_bin = Path(sp) / "nvidia" / "cublas_cu11" / "bin"
        if cublas_bin.exists():
            cuda_paths.append(str(cublas_bin))

    # Add local bin/cuda folder (for portable CUDA DLLs)
    local_cuda = project_root / "bin" / "cuda"
    if local_cuda.exists() and any(local_cuda.iterdir()):
        cuda_paths.append(str(local_cuda))

    # Add CUDA Toolkit paths LAST (less preferred)
    cuda_toolkit_paths = [
        "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.1\\bin",
        "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.2\\bin",
        "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v13.2\\bin",
    ]
    for path in cuda_toolkit_paths:
        if Path(path).exists():
            cuda_paths.append(path)

    # Add Windows System32 LAST (has CUDA runtime but may have incompatible cuDNN)
    cuda_paths.append(str(Path(os.environ.get("SYSTEMROOT", "C:\\Windows")) / "System32"))

    return cuda_paths


def setup_cuda_environment(apply: bool = True) -> str | None:
    """
    Configura las variables de entorno de CUDA.

    Args:
        apply: Si True (default), modifica os.environ["PATH"] globalmente
               para compatibilidad hacia atrás. Si False, retorna el nuevo PATH
               sin modificar el entorno global, para que el caller lo use en
               subprocess.run(env=...) o similar.

    Returns:
        El nuevo PATH si apply=False, None si apply=True.

    Nota: En macOS y Linux sin NVIDIA GPU, retorna el PATH original sin cambios.
    Debe llamarse ANTES de importar librerías que usen CUDA si apply=True.
    """
    cuda_paths = get_cuda_paths()

    if not cuda_paths:
        return None

    new_path = os.pathsep.join(cuda_paths) + os.pathsep + os.environ.get("PATH", "")

    if apply:
        os.environ["PATH"] = new_path

        # Add DLL directories for Python 3.8+ (required for proper DLL loading)
        for path in cuda_paths:
            p = Path(path)
            if p.is_dir():
                with contextlib.suppress(AttributeError, OSError):
                    os.add_dll_directory(str(p))
        return None
    else:
        return new_path


def has_cuda_support() -> bool:
    """
    Verifica si hay soporte de CUDA disponible en el sistema.

    Returns:
        True si hay al menos un path de CUDA válido.
    """
    cuda_paths = get_cuda_paths()
    return len(cuda_paths) > 0


__all__ = [
    "get_cuda_paths",
    "has_cuda_support",
    "setup_cuda_environment",
]
