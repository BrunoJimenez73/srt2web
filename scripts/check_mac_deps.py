"""
Verificador de dependencias para Mac Silicon (ARM64)

Este script verifica que todas las dependencias necesarias estén instaladas
y configuradas correctamente para ejecutar SRT2Web en Mac Silicon.
"""

import platform
import shutil
import subprocess
import sys
from pathlib import Path


def check_architecture() -> bool:
    """Verificar si es Mac Silicon (ARM64)"""
    arch = platform.machine()
    if arch == "arm64":
        print("✓ Arquitectura: Apple Silicon (ARM64)")
        return True
    else:
        print(f"⚠ Arquitectura: {arch} (no es Apple Silicon)")
        print("  Este script está optimizado para Mac Silicon (M1/M2/M3)")
        return False


def check_macos_version() -> bool:
    """Verificar versión de macOS"""
    if platform.system() != "Darwin":
        print("⚠ No es macOS")
        return False

    version_str = platform.mac_ver()[0]
    major_version = int(version_str.split(".")[0])

    if major_version >= 12:
        print(f"✓ macOS: {version_str} (compatible)")
        return True
    else:
        print(f"⚠ macOS {version_str} (se requiere 12+)")
        return False


def check_homebrew() -> bool:
    """Verificar si Homebrew está instalado"""
    if shutil.which("brew"):
        result = subprocess.run(["brew", "--version"], capture_output=True, text=True)
        version = result.stdout.strip().split()[-1] if result.returncode == 0 else "desconocida"
        print(f"✓ Homebrew: {version}")
        return True
    else:
        print("⚠ Homebrew: no instalado (opcional pero recomendado)")
        return False


def check_python() -> bool:
    """Verificar Python 3.12"""
    python_versions = ["python3.12", "python3", "python"]

    for python_cmd in python_versions:
        if shutil.which(python_cmd):
            result = subprocess.run([python_cmd, "--version"], capture_output=True, text=True)
            version_str = result.stdout.strip()

            # Extraer versión
            if "3.12" in version_str or "3.13" in version_str:
                print(f"✓ Python: {version_str}")

                # Verificar si está en entorno virtual
                if sys.prefix != sys.base_prefix:
                    print("  ✓ Entorno virtual: activo")
                else:
                    print("  ⚠ Entorno virtual: no activo")

                return True

    print("✗ Python 3.12: no encontrado")
    print("  Instala Python 3.12 desde python.org o con Homebrew: brew install python@3.12")
    return False


def check_ffmpeg() -> bool:
    """Verificar FFmpeg"""
    if shutil.which("ffmpeg"):
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        first_line = result.stdout.split("\n")[0] if result.stdout else ""
        print(f"✓ FFmpeg: instalado ({first_line})")

        # Verificar VideoToolbox (hardware acceleration en Mac)
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        if "h264_videotoolbox" in result.stdout:
            print("  ✓ VideoToolbox: disponible (hardware encoding)")
        else:
            print("  ⚠ VideoToolbox: no disponible (usando software encoding)")

        return True
    else:
        print("✗ FFmpeg: no encontrado")
        print("  Instala con: brew install ffmpeg")
        return False


def check_nodejs() -> bool:
    """Verificar Node.js"""
    if shutil.which("node"):
        result = subprocess.run(["node", "--version"], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"✓ Node.js: {version}")
        return True
    else:
        print("⚠ Node.js: no encontrado (necesario para construir frontend)")
        return False


def check_pytorch() -> bool:
    """Verificar PyTorch con soporte MPS"""
    try:
        import torch

        # Verificar versión
        print(f"✓ PyTorch: {torch.__version__}")

        # Verificar MPS (Metal Performance Shaders)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("  ✓ MPS (Metal Performance Shaders): disponible")
            return True
        elif torch.cuda.is_available():
            print("  ⚠ CUDA: disponible (no es típico en Mac)")
            return True
        else:
            print("  ⚠ MPS: no disponible (usando CPU)")
            return True  # Aún funciona, solo más lento

    except ImportError:
        print("✗ PyTorch: no instalado")
        print("  Instala con: pip install torch torchvision torchaudio")
        return False
    except Exception as e:
        print(f"✗ PyTorch: error ({e})")
        return False


def check_onnxruntime() -> bool:
    """Verificar ONNX Runtime con soporte CoreML"""
    try:
        import onnxruntime as ort

        providers = ort.get_available_providers()
        print(f"✓ ONNX Runtime: {ort.__version__}")

        if "CoreMLExecutionProvider" in providers:
            print("  ✓ CoreML: disponible (GPU Apple Silicon)")
            return True
        elif "CUDAExecutionProvider" in providers:
            print("  ⚠ CUDA: disponible (no es típico en Mac)")
            return True
        else:
            print("  ⚠ CoreML: no disponible (usando CPU)")
            return True  # Aún funciona, solo más lento

    except ImportError:
        print("⚠ ONNX Runtime: no instalado (opcional, para Piper TTS)")
        return True  # No es crítico
    except Exception as e:
        print(f"⚠ ONNX Runtime: error ({e})")
        return True


def check_venv() -> bool:
    """Verificar entorno virtual"""
    venv_path = Path("venv")
    if venv_path.exists():
        print("✓ Entorno virtual: existe")
        return True
    else:
        print("⚠ Entorno virtual: no encontrado")
        print("  Ejecuta: ./install_Mac.sh")
        return False


def check_config() -> bool:
    """Verificar archivo de configuración"""
    config_path = Path("config.yaml")
    if config_path.exists():
        print("✓ Configuración: config.yaml existe")
        return True
    else:
        print("⚠ Configuración: config.yaml no encontrado")
        print("  Se creará automáticamente al iniciar")
        return True


def check_frontend() -> bool:
    """Verificar frontend construido"""
    static_path = Path("server/static/index.html")
    if static_path.exists():
        print("✓ Frontend: construido")
        return True
    else:
        print("⚠ Frontend: no construido")
        print("  Se construirá automáticamente al iniciar")
        return True


def print_summary(results: dict) -> None:
    """Imprimir resumen de verificaciones"""
    print("\n" + "=" * 50)
    print("           RESUMEN")
    print("=" * 50)

    critical = ["python", "ffmpeg", "pytorch", "venv"]
    optional = ["homebrew", "nodejs", "onnxruntime", "config", "frontend"]

    all_ok = True
    for key in critical:
        status = "✓" if results.get(key, False) else "✗"
        if not results.get(key, False):
            all_ok = False
        print(f"  {status} {key.upper()}")

    for key in optional:
        status = "✓" if results.get(key, False) else "⚠"
        print(f"  {status} {key.upper()} (opcional)")

    print()

    if all_ok:
        print("¡Todo está listo para ejecutar SRT2Web en Mac Silicon!")
        print("\nPara iniciar:")
        print("  ./start_Mac.sh")
    else:
        print("Faltan dependencias críticas. Ejecuta:")
        print("  ./install_Mac.sh")


def main() -> int:
    """Función principal"""
    print("=" * 50)
    print("     SRT2Web - Verificador Mac Silicon")
    print("=" * 50)
    print()

    results = {}

    # Verificaciones de sistema
    print("[SISTEMA]")
    results["architecture"] = check_architecture()
    results["macos"] = check_macos_version()
    print()

    # Verificaciones de dependencias
    print("[DEPENDENCIAS]")
    results["homebrew"] = check_homebrew()
    results["python"] = check_python()
    results["ffmpeg"] = check_ffmpeg()
    results["nodejs"] = check_nodejs()
    print()

    # Verificaciones de Python
    print("[PYTHON]")
    results["pytorch"] = check_pytorch()
    results["onnxruntime"] = check_onnxruntime()
    results["venv"] = check_venv()
    print()

    # Verificaciones del proyecto
    print("[PROYECTO]")
    results["config"] = check_config()
    results["frontend"] = check_frontend()
    print()

    # Resumen
    print_summary(results)

    # Retornar código de salida
    critical_ok = all(
        [
            results.get("python", False),
            results.get("ffmpeg", False),
            results.get("pytorch", False),
            results.get("venv", False),
        ]
    )

    return 0 if critical_ok else 1


if __name__ == "__main__":
    sys.exit(main())
