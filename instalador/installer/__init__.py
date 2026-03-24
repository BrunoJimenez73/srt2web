"""
Modulo de instalacion de SRT2Web
Maneja la instalacion de componentes del sistema
"""

import os
import sys
import subprocess
import shutil
import platform
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, Optional
import logging

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("installer")

_install_status: Dict[str, dict] = {}
_server_process: Optional[subprocess.Popen] = None


def check_system() -> Dict:
    """Verifica el estado del sistema."""
    result = {
        "python": _check_python(),
        "ffmpeg": _check_ffmpeg(),
        "node": _check_node(),
        "gpu": _check_gpu(),
    }
    return result


def _check_python() -> Dict:
    """Verifica Python."""
    try:
        result = subprocess.run(
            ["python", "--version"], capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip() or result.stderr.strip()
        version = version.replace("Python ", "")
        return {"available": True, "version": version}
    except Exception:
        return {"available": False, "version": None}


def _check_ffmpeg() -> Dict:
    """Verifica FFmpeg."""
    bin_path = PROJECT_ROOT / "bin"
    ffmpeg_path = None

    if platform.system() == "Windows":
        ffmpeg_local = bin_path / "ffmpeg.exe"
        if ffmpeg_local.exists():
            ffmpeg_path = str(ffmpeg_local)
    else:
        ffmpeg_local = bin_path / "ffmpeg"
        if ffmpeg_local.exists():
            ffmpeg_path = str(ffmpeg_local)

    if not ffmpeg_path:
        try:
            result = subprocess.run(
                ["where", "ffmpeg"]
                if platform.system() == "Windows"
                else ["which", "ffmpeg"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                ffmpeg_path = result.stdout.strip().split("\n")[0]
        except Exception:
            pass

    if ffmpeg_path:
        try:
            result = subprocess.run(
                [ffmpeg_path, "-version"], capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                version_line = result.stderr.split("\n")[0]
                version = (
                    version_line.split(" ")[2]
                    if "version" in version_line
                    else "unknown"
                )
                return {"available": True, "version": version, "path": ffmpeg_path}
        except Exception:
            pass

    return {"available": False, "version": None}


def _check_node() -> Dict:
    """Verifica Node.js."""
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=5
        )
        version = result.stdout.strip().replace("v", "")
        return {"available": True, "version": version}
    except Exception:
        return {"available": False, "version": None}


def _check_gpu() -> Dict:
    """Verifica GPU NVIDIA."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return {"available": True, "name": result.stdout.strip()}
    except Exception:
        pass

    return {"available": False}


async def install_component(component: str, progress_callback=None) -> bool:
    """Instala un componente especifico."""
    global _install_status

    _install_status[component] = {
        "status": "installing",
        "progress": 0,
        "message": "Iniciando...",
    }

    try:
        installers = {
            "ffmpeg": _install_ffmpeg,
            "deps": _install_python_deps,
            "node": _install_node_deps,
            "whisper-tiny": lambda cb: _install_whisper("tiny", cb),
            "piper": _install_piper_voices,
            "gpu": _install_gpu_support,
        }

        if component in installers:
            success = await installers[component](progress_callback)
        else:
            _install_status[component]["message"] = (
                f"Componente desconocido: {component}"
            )
            success = False

        if success:
            _install_status[component]["status"] = "done"
            _install_status[component]["progress"] = 100
            _install_status[component]["message"] = "Completado"
        else:
            _install_status[component]["status"] = "error"

        return success

    except Exception as e:
        _install_status[component]["status"] = "error"
        _install_status[component]["message"] = str(e)
        logger.error(f"Error installing {component}: {e}")
        return False


async def _install_ffmpeg(progress_callback) -> bool:
    """Descarga e instala FFmpeg."""
    bin_path = PROJECT_ROOT / "bin"
    bin_path.mkdir(exist_ok=True)

    _install_status["ffmpeg"]["message"] = "Descargando FFmpeg..."

    if platform.system() == "Windows":
        return await _install_ffmpeg_windows(bin_path, progress_callback)
    elif platform.system() == "Darwin":
        return await _install_ffmpeg_mac(progress_callback)
    else:
        return await _install_ffmpeg_linux(progress_callback)


async def _install_ffmpeg_windows(bin_path: Path, progress_callback) -> bool:
    """Instala FFmpeg en Windows."""
    url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    zip_path = bin_path / "ffmpeg.zip"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    _install_status["ffmpeg"]["message"] = f"Error: {response.status}"
                    return False

                total_size = int(response.headers.get("content-length", 0))
                downloaded = 0

                with open(zip_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = int((downloaded / total_size) * 100)
                            _install_status["ffmpeg"]["progress"] = progress
                            if progress_callback:
                                await progress_callback("ffmpeg", progress)

        _install_status["ffmpeg"]["message"] = "Extrayendo..."

        import zipfile

        with zipfile.ZipFile(zip_path, "r") as zf:
            for file in zf.namelist():
                if "ffmpeg.exe" in file or "ffprobe.exe" in file:
                    zf.extract(file, bin_path)

        for f in bin_path.glob("**/ffmpeg.exe"):
            shutil.move(str(f), bin_path / "ffmpeg.exe")
        for f in bin_path.glob("**/ffprobe.exe"):
            shutil.move(str(f), bin_path / "ffprobe.exe")

        zip_path.unlink()

        _install_status["ffmpeg"]["message"] = "FFmpeg instalado"
        return True

    except Exception as e:
        _install_status["ffmpeg"]["message"] = str(e)
        return False


async def _install_ffmpeg_mac(progress_callback) -> bool:
    """Instala FFmpeg en macOS."""
    try:
        result = subprocess.run(
            ["brew", "install", "ffmpeg"], capture_output=True, text=True, timeout=300
        )
        return result.returncode == 0
    except Exception as e:
        _install_status["ffmpeg"]["message"] = str(e)
        return False


async def _install_ffmpeg_linux(progress_callback) -> bool:
    """Instala FFmpeg en Linux."""
    try:
        result = subprocess.run(
            ["sudo", "apt", "install", "-y", "ffmpeg"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return result.returncode == 0
    except Exception as e:
        _install_status["ffmpeg"]["message"] = str(e)
        return False


async def _install_python_deps(progress_callback) -> bool:
    """Instala dependencias Python."""
    _install_status["deps"]["message"] = "Instalando..."

    req_file = PROJECT_ROOT / "requirements.txt"

    try:
        _install_status["deps"]["progress"] = 25

        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(PROJECT_ROOT),
        )

        _install_status["deps"]["progress"] = 100

        if result.returncode == 0:
            return True
        else:
            _install_status["deps"]["message"] = (
                result.stderr[:200] if result.stderr else "Error"
            )
            return False

    except Exception as e:
        _install_status["deps"]["message"] = str(e)
        return False


async def _install_node_deps(progress_callback) -> bool:
    """Instala dependencias Node.js."""
    _install_status["node"]["message"] = "Instalando..."

    frontend_path = PROJECT_ROOT / "frontend"
    if not frontend_path.exists():
        _install_status["node"]["message"] = "Directorio frontend no encontrado"
        return False

    try:
        result = subprocess.run(
            ["npm", "install"],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(frontend_path),
        )

        _install_status["node"]["progress"] = 100

        if result.returncode == 0:
            return True
        else:
            _install_status["node"]["message"] = (
                result.stderr[:200] if result.stderr else "Error"
            )
            return False

    except Exception as e:
        _install_status["node"]["message"] = str(e)
        return False


async def _install_whisper(model_size: str, progress_callback) -> bool:
    """Descarga modelo Whisper."""
    _install_status["whisper-tiny"]["message"] = f"Descargando Whisper {model_size}..."

    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                f"from faster_whisper import WhisperModel; WhisperModel('{model_size}', device='cpu', compute_type='int8')",
            ],
            capture_output=True,
            text=True,
            timeout=1800,
            cwd=str(PROJECT_ROOT),
        )

        _install_status["whisper-tiny"]["progress"] = 100

        if result.returncode == 0:
            return True
        else:
            _install_status["whisper-tiny"]["message"] = (
                result.stderr[:200] if result.stderr else "Error"
            )
            return False

    except Exception as e:
        _install_status["whisper-tiny"]["message"] = str(e)
        return False


async def _install_piper_voices(progress_callback) -> bool:
    """Descarga voces de Piper TTS."""
    _install_status["piper"]["message"] = "Descargando voces..."

    models_dir = PROJECT_ROOT / "models" / "piper"
    models_dir.mkdir(parents=True, exist_ok=True)

    voices = [
        (
            "es_ES-davefx-medium.onnx",
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        ),
        (
            "es_ES-davefx-medium.onnx.json",
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
        ),
    ]

    try:
        async with aiohttp.ClientSession() as session:
            for i, (filename, url) in enumerate(voices):
                _install_status["piper"]["message"] = f"Descargando {filename}..."
                progress = int((i / len(voices)) * 100)
                _install_status["piper"]["progress"] = progress

                dest = models_dir / filename

                async with session.get(url) as response:
                    if response.status != 200:
                        continue

                    with open(dest, "wb") as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)

        _install_status["piper"]["progress"] = 100
        return True

    except Exception as e:
        _install_status["piper"]["message"] = str(e)
        return False


async def _install_gpu_support(progress_callback) -> bool:
    """Instala soporte GPU (torch, onnxruntime-gpu)."""
    _install_status["gpu"]["message"] = "Verificando CUDA..."

    cuda_version = None
    try:
        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "CUDA Version:" in line:
                    cuda_version = line.split("CUDA Version:")[1].strip().split(".")[0]
                    break
    except Exception:
        pass

    _install_status["gpu"]["message"] = f"CUDA {cuda_version or 'CPU'} detectada"

    torch_index = "https://download.pytorch.org/whl/cu121"
    packages = [("torch", torch_index), ("onnxruntime-gpu", None)]

    for i, (pkg, index_url) in enumerate(packages):
        _install_status["gpu"]["message"] = f"Instalando {pkg}..."
        progress = int((i / len(packages)) * 100)
        _install_status["gpu"]["progress"] = progress

        try:
            cmd = [sys.executable, "-m", "pip", "install", pkg, "--quiet"]
            if index_url:
                cmd.extend(["--index-url", index_url])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800 if pkg == "torch" else 600,
                cwd=str(PROJECT_ROOT),
            )

            if result.returncode != 0:
                logger.warning(
                    f"GPU install warning for {pkg}: {result.stderr[:200] if result.stderr else ''}"
                )

        except Exception as e:
            logger.warning(f"GPU install exception for {pkg}: {e}")

    _install_status["gpu"]["progress"] = 100
    _install_status["gpu"]["message"] = "GPU instalado"
    return True


def get_install_status() -> Dict:
    """Obtiene el estado actual de la instalacion."""
    global _install_status

    results = []
    all_done = True

    for component, data in _install_status.items():
        results.append(
            {
                "component": component,
                "status": data.get("status", "pending"),
                "progress": data.get("progress", 0),
                "message": data.get("message", ""),
            }
        )
        if data.get("status") not in ["done", "error"]:
            all_done = False

    return {"results": results, "all_done": all_done}


def reset_install_status():
    """Resetea el estado de la instalacion."""
    global _install_status
    _install_status = {}
    logger.info("Installation status reset")


def uninstall_component(component: str) -> bool:
    """Desinstala un componente."""
    try:
        if component == "ffmpeg":
            bin_path = PROJECT_ROOT / "bin"
            ffmpeg = bin_path / "ffmpeg.exe"
            ffprobe = bin_path / "ffprobe.exe"
            if ffmpeg.exists():
                ffmpeg.unlink()
            if ffprobe.exists():
                ffprobe.unlink()
            return True

        elif component == "deps":
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "uninstall",
                    "-y",
                    "-r",
                    str(PROJECT_ROOT / "requirements.txt"),
                ],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0

        elif component == "whisper-tiny":
            result = subprocess.run(
                [sys.executable, "-m", "pip", "uninstall", "-y", "faster-whisper"],
                capture_output=True,
                text=True,
                timeout=300,
            )
            return result.returncode == 0

        elif component == "piper":
            models_dir = PROJECT_ROOT / "models" / "piper"
            if models_dir.exists():
                shutil.rmtree(models_dir)
            return True

        elif component == "gpu":
            for pkg in ["torch", "onnxruntime-gpu"]:
                subprocess.run(
                    [sys.executable, "-m", "pip", "uninstall", "-y", pkg],
                    capture_output=True,
                    timeout=300,
                )
            return True

        return False

    except Exception as e:
        logger.error(f"Error uninstalling {component}: {e}")
        return False


def start_server() -> tuple[bool, str]:
    """Inicia el servidor principal."""
    global _server_process

    if is_server_running():
        return True, ""

    try:
        import platform

        python_cmd = "python.exe" if platform.system() == "Windows" else "python"

        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)

        _server_process = subprocess.Popen(
            [python_cmd, "main.py"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        import time

        time.sleep(3)

        if is_server_running():
            return True, ""
        else:
            if _server_process.poll() is not None:
                return False, "El servidor no pudo iniciar"
            return False, "El servidor no responde en el puerto 9999"

    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return False, str(e)


def is_server_running() -> bool:
    """Verifica si el servidor principal esta corriendo."""
    try:
        import requests

        r = requests.get("http://localhost:9999", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def shutdown_server():
    """Cierra el servidor del instalador."""
    global _server_process
    if _server_process:
        _server_process.terminate()
