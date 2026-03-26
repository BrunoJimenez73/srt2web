"""
RTMP Server - Wrapper para Node Media Server.

Inicia y gestiona el servidor RTMP de Node.js como proceso hijo.
"""

import os
import sys
import subprocess
import logging
import threading
import time
import signal
import socket
from pathlib import Path
from typing import Optional

logger = logging.getLogger("srt2web.rtmp_server")

NMS_DIR = Path(__file__).parent.parent / "rtmp_server"
NMS_SCRIPT = NMS_DIR / "server.js"


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


class RTMPServer:
    """Gestor del servidor RTMP Node Media Server."""
    
    _instance: Optional['RTMPServer'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._process: Optional[subprocess.Popen] = None
        self._monitor_thread: Optional[threading.Thread] = None
        self._running = False
    
    @property
    def is_running(self) -> bool:
        return self._running and self._process is not None and self._process.poll() is None
    
    def start(self, port: int = 1935) -> bool:
        """Iniciar el servidor RTMP."""
        if is_port_in_use(port):
            logger.info(f"RTMP Server ya está corriendo en puerto {port}")
            self._running = True
            return True
        
        if self.is_running:
            logger.info("RTMP Server ya está corriendo")
            return True
        
        if not NMS_SCRIPT.exists():
            logger.error(f"NMS script no encontrado: {NMS_SCRIPT}")
            return False
        
        try:
            logger.info(f"Iniciando RTMP Server en puerto {port}...")
            
            env = os.environ.copy()
            env.update({
                'NODE_ENV': 'production',
            })
            
            self._process = subprocess.Popen(
                ['node', str(NMS_SCRIPT)],
                cwd=str(NMS_DIR),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=(
                    subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                ),
            )
            
            self._running = True
            
            self._monitor_thread = threading.Thread(
                target=self._monitor_process,
                daemon=True,
                name="rtmp-server-monitor",
            )
            self._monitor_thread.start()
            
            time.sleep(1)
            
            if self._process.poll() is not None:
                logger.error("RTMP Server murió inmediatamente")
                return False
            
            logger.info("RTMP Server iniciado correctamente")
            return True
            
        except Exception as e:
            logger.error(f"Error al iniciar RTMP Server: {e}")
            return False
    
    def stop(self) -> None:
        """Detener el servidor RTMP."""
        if not self._running:
            return
        
        self._running = False
        
        if self._process:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self._process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self._process.terminate()
                
                self._process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error al detener RTMP Server: {e}")
                try:
                    self._process.kill()
                except:
                    pass
            finally:
                self._process = None
        
        logger.info("RTMP Server detenido")
    
    def _monitor_process(self) -> None:
        """Monitorear el proceso del servidor."""
        while self._running and self._process:
            if self._process.poll() is not None:
                logger.error(f"RTMP Server murió con código {self._process.returncode}")
                self._running = False
                break
            time.sleep(1)
    
    def get_stream_url(self, stream_key: str = "stream") -> str:
        """Obtener URL del stream."""
        return f"rtmp://localhost:1935/live/{stream_key}"


def get_rtmp_server() -> RTMPServer:
    """Obtener instancia singleton del servidor RTMP."""
    return RTMPServer()


def start_rtmp_server(port: int = 1935) -> bool:
    """Iniciar el servidor RTMP."""
    return get_rtmp_server().start(port)


def stop_rtmp_server() -> None:
    """Detener el servidor RTMP."""
    get_rtmp_server().stop()
