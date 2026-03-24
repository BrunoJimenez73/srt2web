"""
API del instalador SRT2Web
Servidor web para el instalador visual
"""

import os
import sys
import asyncio
import signal
import logging
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from instalador.installer import (
    check_system,
    install_component,
    get_install_status,
    start_server,
    is_server_running,
    reset_install_status,
    uninstall_component,
    shutdown_server,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("installer_api")

app = FastAPI(title="SRT2Web Installer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_install_task: Optional[asyncio.Task] = None
_shutdown_event = asyncio.Event()


class InstallRequest(BaseModel):
    components: List[str]


class UninstallRequest(BaseModel):
    component: str


@app.get("/api/installer/check")
async def api_check_system():
    """Verifica el estado del sistema."""
    return check_system()


@app.post("/api/installer/install")
async def api_install(req: InstallRequest):
    """Inicia la instalacion de componentes."""
    global _install_task

    if _install_task is not None and not _install_task.done():
        raise HTTPException(status_code=400, detail="Instalacion en progreso")

    async def run_installs():
        for component in req.components:
            await install_component(component)

    _install_task = asyncio.create_task(run_installs())

    return {"status": "started", "components": req.components}


@app.get("/api/installer/status")
async def api_install_status():
    """Obtiene el estado de la instalacion."""
    return get_install_status()


@app.post("/api/installer/uninstall")
async def api_uninstall(req: UninstallRequest):
    """Desinstala un componente."""
    success = uninstall_component(req.component)
    return {"status": "ok" if success else "error", "component": req.component}


@app.post("/api/installer/start-server")
async def api_start_server():
    """Inicia el servidor principal."""
    if is_server_running():
        return {"status": "already_running", "url": "http://localhost:9999"}

    success, error_msg = start_server()

    if success:
        await asyncio.sleep(2)
        return {"status": "started", "url": "http://localhost:9999"}
    else:
        raise HTTPException(status_code=500, detail=f"Error: {error_msg}")


@app.post("/api/installer/reset")
async def api_reset():
    """Resetea el estado de la instalacion."""
    reset_install_status()
    return {"status": "reset"}


@app.post("/api/installer/shutdown")
async def api_shutdown():
    """Cierra el servidor del instalador."""
    logger.info("Shutdown requested")
    _shutdown_event.set()
    return {"status": "shutdown"}


@app.get("/api/installer/is-running")
async def api_is_running():
    """Verifica si el servidor principal esta corriendo."""
    return {"running": is_server_running()}


@app.get("/")
async def serve_installer():
    """Sirve el instalador HTML."""
    html_path = Path(__file__).parent / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(status_code=404, detail="Instalador no encontrado")


async def wait_for_shutdown():
    """Espera la senal de apagado."""
    await _shutdown_event.wait()


def run_server():
    """Ejecuta el servidor."""
    import uvicorn

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop=loop, log_level="info")
    server = uvicorn.Server(config)

    async def run_with_shutdown():
        task = asyncio.create_task(server.serve())
        shutdown_task = asyncio.create_task(wait_for_shutdown())

        done, pending = await asyncio.wait(
            [task, shutdown_task], return_when=asyncio.FIRST_COMPLETED
        )

        for t in pending:
            t.cancel()

        server.should_exit = True

    loop.run_until_complete(run_with_shutdown())


if __name__ == "__main__":
    run_server()
