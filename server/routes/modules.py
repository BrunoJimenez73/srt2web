"""
Module management routes for SRT2Web API.
"""

import logging
import traceback
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from server.validators import ModuleToggle, sanitize_module_name

logger = logging.getLogger("srt2web.api.modules")

router = APIRouter(tags=["modules"])


def _ctx(request: Request) -> dict[str, Any]:
    return request.app.state.ctx  # type: ignore[no-any-return]


@router.get("/modules")
async def list_modules(request: Request) -> dict[str, Any]:
    """List all registered modules and their status."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    return {"modules": [m.get_status().to_dict() for m in pipeline.get_modules()]}


@router.get("/modules/{module_name}/debug")
async def debug_module(request: Request, module_name: str) -> dict[str, Any]:
    """Debug endpoint to see raw module state."""
    try:
        safe_module_name = sanitize_module_name(module_name)
    except ValueError as e:
        raise HTTPException(400, str(e))

    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    module = pipeline.get_module(safe_module_name)
    if not module:
        raise HTTPException(404, f"Module '{safe_module_name}' not found")
    return {
        "name": module.name,
        "enabled": module.enabled,
        "state": str(module.state),
    }


@router.put("/modules/{module_name}/toggle")
async def toggle_module(
    request: Request,
    module_name: str,
    body: ModuleToggle,
) -> dict[str, Any]:
    """Enable or disable a module with hot reload."""

    try:
        safe_module_name = sanitize_module_name(module_name)
    except ValueError as e:
        raise HTTPException(400, str(e))

    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    config = ctx["config"]

    module = pipeline.get_module(safe_module_name)
    if not module:
        raise HTTPException(404, f"Module '{safe_module_name}' not found")

    was_enabled = module.enabled
    module.enabled = body.enabled
    config.set_module_enabled(safe_module_name, body.enabled)
    config.save()

    # Hot reload: start or stop the module if pipeline is running
    if pipeline.state.value == "running":
        try:
            if body.enabled and not was_enabled:
                # Module was disabled, now enabled - start it
                mod_config = config.get_module_config(safe_module_name)
                module.configure(mod_config)
                module.start()
                logger.info(f"Hot-started module: {safe_module_name}")
            elif not body.enabled and was_enabled:
                # Module was enabled, now disabled - stop it
                module.stop()
                logger.info(f"Hot-stopped module: {safe_module_name}")
            else:
                # Just reconfigure
                pipeline.reconfigure(config)
        except Exception as e:
            err_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            logger.error(f"Error in hot-reload for {safe_module_name}: {err_msg}")
            return {
                "module": safe_module_name,
                "enabled": body.enabled,
                "status": module.get_status().to_dict(),
                "warning": f"Hot reload failed: {e!s}",
                "error": err_msg,
            }
    else:
        pipeline.reconfigure(config)

    return {
        "module": safe_module_name,
        "enabled": body.enabled,
        "status": module.get_status().to_dict(),
        "hot_reload": True,
    }
