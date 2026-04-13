"""
CUDA Paths Configuration - Extraído de main.py

Maneja la configuración de paths de CUDA/cuDNN para Windows.
Extraído para mejorar mantenibilidad.
"""

import os
import site
from typing import List


def get_cuda_paths() -> List[str]:
    """
    Recolecta todos los paths de CUDA/cuDNN disponibles en el sistema.
    
    Returns:
        Lista de paths priorizados para CUDA (cuDNN 8.x primero).
    """
    cuda_paths: List[str] = []
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # CRITICAL: Add local cuDNN 8.x FIRST (must be at front to avoid loading cuDNN 9.x)
    local_cudnn8 = os.path.join(project_root, "bin", "cudnn8")
    if os.path.exists(local_cudnn8) and os.listdir(local_cudnn8):
        cuda_paths.append(local_cudnn8)  # Prioritize cuDNN 8.x
    
    # Add venv nvidia paths (cuDNN 8.9.4 from pip)
    for sp in site.getsitepackages():
        cudnn_bin = os.path.join(sp, "nvidia", "cudnn", "bin")
        if os.path.exists(cudnn_bin):
            cuda_paths.append(cudnn_bin)
        cublas_bin = os.path.join(sp, "nvidia", "cublas_cu11", "bin")
        if os.path.exists(cublas_bin):
            cuda_paths.append(cublas_bin)
    
    # Add local bin/cuda folder (for portable CUDA DLLs)
    local_cuda = os.path.join(project_root, "bin", "cuda")
    if os.path.exists(local_cuda) and os.listdir(local_cuda):
        cuda_paths.append(local_cuda)
    
    # Add CUDA Toolkit paths LAST (less preferred)
    cuda_toolkit_paths = [
        "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.1\\bin",
        "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.2\\bin",
        "C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v13.2\\bin",
    ]
    for path in cuda_toolkit_paths:
        if os.path.exists(path):
            cuda_paths.append(path)
    
    # Add Windows System32 LAST (has CUDA runtime but may have incompatible cuDNN)
    cuda_paths.append(os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32"))
    
    return cuda_paths


def setup_cuda_environment() -> None:
    """
    Configura las variables de entorno de CUDA para el proceso actual.
    Debe llamarse ANTES de importar librerías que usen CUDA.
    """
    cuda_paths = get_cuda_paths()
    
    if cuda_paths:
        os.environ["PATH"] = os.pathsep.join(cuda_paths) + os.pathsep + os.environ.get("PATH", "")
        
        # Add DLL directories for Python 3.8+ (required for proper DLL loading)
        for path in cuda_paths:
            if os.path.isdir(path):
                try:
                    os.add_dll_directory(path)
                except (AttributeError, OSError):
                    pass  # Not all paths support add_dll_directory


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
    "setup_cuda_environment",
    "has_cuda_support",
]