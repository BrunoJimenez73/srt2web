"""
Output management routes for SRT2Web API.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from core.io_factory import OutputFactory
from server.validators import AddOutputRequest, UpdateOutputRequest

logger = logging.getLogger("srt2web.api.outputs")

router = APIRouter(tags=["outputs"])

from server.ctx import get_ctx as _ctx

_CANONICAL_OUTPUT_TYPES = frozenset({"web", "srt", "rtmp", "file", "recording", "webrtc"})

# F151: Keys that should never appear in untrusted output config dicts
_FORBIDDEN_CONFIG_KEYS = frozenset({"command", "shell", "exec", "eval", "__import__", "subprocess"})


def _validate_output_config(config: dict[str, Any]) -> None:
    """F151: Reject output config dicts containing dangerous keys."""
    for key in config:
        key_lower = key.lower() if isinstance(key, str) else ""
        if key_lower in _FORBIDDEN_CONFIG_KEYS:
            raise HTTPException(400, f"Forbidden config key: {key}")
        if isinstance(config[key], dict):
            _validate_output_config(config[key])


def _normalize_output_type(output_type: str | None) -> str:
    """Normaliza un tipo de output a un valor canónico aceptado por ``OutputTypeEnum``.

    Bug F106: ``OutputFactory.resolve_type`` devuelve el primer nombre registrado
    para una clase (p.ej. ``"webplayer"`` en lugar de ``"web"``). Si este valor se
    guarda tal cual en ``config.yaml``, la siguiente ``PUT /api/config`` falla con
    un 400 de Pydantic porque ``OutputTypeEnum`` solo acepta los nombres canónicos.
    Mapeamos explícitamente los alias a su forma canónica.
    """
    if not output_type:
        return "web"
    if output_type in _CANONICAL_OUTPUT_TYPES:
        return output_type
    if output_type in {"webplayer", "hls"}:
        return "web"
    return "web"


def _sync_outputs_to_config(request: Request, composite: Any) -> None:
    """Actualiza la lista `outputs` en config.yaml desde el estado actual del composite."""
    ctx = _ctx(request)
    config = ctx["config"]

    from core.io_factory import OutputFactory

    output_list = []
    for name in composite.get_output_names() if hasattr(composite, "get_output_names") else []:
        output = composite.get_output_by_name(name) if hasattr(composite, "get_output_by_name") else None
        if not output:
            continue
        # Use actual output type from OutputFactory registry metadata
        output_type = getattr(output, "output_type", None)
        if not output_type:
            # Fallback: reverse-lookup from factory registry
            output_type = OutputFactory.resolve_type(type(output).__name__) or name
        # Normalize to canonical name (F106: avoid persisting alias like "webplayer")
        output_type = _normalize_output_type(output_type)
        entry = {
            "name": name,
            "type": output_type,
            "enabled": getattr(output, "enabled", True),
            "config": getattr(output, "config", {}),
        }
        output_list.append(entry)

    config.set("output.outputs", output_list)
    try:
        config.save()
    except Exception as e:
        logger.warning(f"Could not sync outputs to config: {e}")


def _get_composite(pipeline: Any) -> Any:
    """Helper: obtiene el CompositeOutput del pipeline. Lanza 500 si no existe."""
    composite = pipeline.get_output_sinks()
    if composite is None:
        composite = pipeline.get_output_sink()
    if composite is None:
        raise HTTPException(500, "No output sink configured in pipeline")
    # Si es un sink simple (no composite), envolverlo sería complejo;
    # en la nueva arquitectura siempre arranca como CompositeOutput.
    return composite


@router.get("/outputs")
async def list_outputs(request: Request) -> dict[str, Any]:
    """Lista todos los outputs configurados con su estado."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    composite = _get_composite(pipeline)

    if hasattr(composite, "get_all_output_statuses"):
        return {"outputs": composite.get_all_output_statuses()}

    # Fallback para sink simple
    status = composite.get_status() if hasattr(composite, "get_status") else {}
    if hasattr(status, "to_dict"):
        status = status.to_dict()
    return {
        "outputs": [
            {
                "name": getattr(composite, "name", "output"),
                "type": OutputFactory.resolve_type(type(composite).__name__) or "unknown",
                "state": status.get("state", "idle"),
                "enabled": True,
                "processed_chunks": status.get("processed_chunks", 0),
                "last_process_time_ms": status.get("last_process_time_ms", 0),
                "stream_info": composite.get_stream_info() if hasattr(composite, "get_stream_info") else {},
            }
        ]
    }


@router.get("/outputs/available")
async def get_available_outputs(request: Request) -> dict[str, Any]:
    """Tipos de output disponibles para crear."""
    from core.io_factory import OutputFactory

    return {"available_types": OutputFactory.available()}


@router.post("/outputs")
async def add_output(request: Request, body: AddOutputRequest) -> dict[str, Any]:
    """Añade un nuevo output al pipeline en caliente y lo guarda en config.yaml."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]

    output_type = body.type
    output_config = body.config or {}
    output_name = body.name or f"{output_type}_{int(time.time())}"

    # F151: Validate output config before passing to factory
    if output_config:
        _validate_output_config(output_config)

    from core.io_factory import OutputFactory

    try:
        output = OutputFactory.create(output_type, output_config)
        output.name = output_name
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    composite = _get_composite(pipeline)

    if hasattr(composite, "add_output"):
        composite.add_output(output_name, output)
        # Iniciar la nueva salida solo si el pipeline está corriendo
        if pipeline.is_running:
            try:
                output.start()
            except Exception as e:
                logger.warning(f"Output '{output_name}' start warning: {e}")
    else:
        raise HTTPException(500, "Pipeline sink does not support multiple outputs")

    # Sync to config.yaml para persistencia
    _sync_outputs_to_config(request, composite)

    return {"status": "added", "name": output_name, "type": output_type}


@router.put("/outputs/{output_name}")
async def update_output(request: Request, output_name: str, body: UpdateOutputRequest) -> dict[str, Any]:
    """Actualiza la configuración de un output existente."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    composite = _get_composite(pipeline)

    if not hasattr(composite, "get_output_by_name"):
        raise HTTPException(404, "Composite output not available")

    output = composite.get_output_by_name(output_name)
    if not output:
        raise HTTPException(404, f"Output '{output_name}' not found")

    if body.config is not None and hasattr(output, "configure"):
        # F151: Validate output config before applying
        _validate_output_config(body.config)
        output.configure(body.config)

    if body.enabled is not None and hasattr(composite, "enable_output"):
        composite.enable_output(output_name, body.enabled)

    return {"status": "updated", "name": output_name}


@router.delete("/outputs/{output_name}")
async def remove_output(request: Request, output_name: str) -> dict[str, Any]:
    """Elimina un output del pipeline y lo elimina de config.yaml."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    composite = _get_composite(pipeline)

    if not hasattr(composite, "remove_output"):
        raise HTTPException(404, "Composite output not available")

    # No permitir eliminar el último output
    if hasattr(composite, "get_output_names") and len(composite.get_output_names()) <= 1:
        raise HTTPException(400, "Cannot remove the last output. Add another output first.")

    if not composite.remove_output(output_name):
        raise HTTPException(404, f"Output '{output_name}' not found")

    # Sync to config.yaml
    _sync_outputs_to_config(request, composite)

    return {"status": "removed", "name": output_name}


@router.post("/outputs/{output_name}/toggle")
async def toggle_output(request: Request, output_name: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Habilita o deshabilita un output."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]
    composite = _get_composite(pipeline)

    output = composite.get_output_by_name(output_name)
    if not output:
        raise HTTPException(404, f"Output '{output_name}' not found")

    enabled = (
        body.get("enabled", not composite.is_output_enabled(output_name))
        if body
        else not composite.is_output_enabled(output_name)
    )
    composite.enable_output(output_name, enabled)

    # Sync to config.yaml
    _sync_outputs_to_config(request, composite)

    return {"status": "toggled", "name": output_name, "enabled": enabled}
