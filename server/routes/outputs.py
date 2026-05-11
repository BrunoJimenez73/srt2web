"""
Output management routes for SRT2Web API.
"""

import logging

from fastapi import APIRouter, HTTPException, Request

from server.validators import AddOutputRequest, UpdateOutputRequest

logger = logging.getLogger("srt2web.api.outputs")

router = APIRouter(tags=["outputs"])


def _ctx(request: Request) -> dict:
    return request.app.state.ctx


def _sync_outputs_to_config(request: Request, composite) -> None:
    """Actualiza la lista `outputs` en config.yaml desde el estado actual del composite."""
    ctx = _ctx(request)
    config = ctx["config"]

    output_list = []
    for name in composite.get_output_names() if hasattr(composite, "get_output_names") else []:
        output = composite.get_output_by_name(name) if hasattr(composite, "get_output_by_name") else None
        if not output:
            continue
        entry = {
            "name": name,
            "type": getattr(output, "name", name.rsplit("_", 1)[0] if "_" in name else name),
            "enabled": getattr(output, "enabled", True),
            "config": getattr(output, "config", {}),
        }
        # Extraer el type real del output
        type_attr = getattr(output, "name", "").rsplit("_", 1)
        entry["type"] = type_attr[0] if len(type_attr) > 1 else name
        output_list.append(entry)

    config.set("output.outputs", output_list)
    try:
        config.save()
    except Exception as e:
        logger.warning(f"Could not sync outputs to config: {e}")


def _get_composite(pipeline):
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
async def list_outputs(request: Request):
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
                "type": getattr(composite, "name", "web"),
                "state": status.get("state", "idle"),
                "enabled": True,
                "processed_chunks": status.get("processed_chunks", 0),
                "last_process_time_ms": status.get("last_process_time_ms", 0),
                "stream_info": composite.get_stream_info() if hasattr(composite, "get_stream_info") else {},
            }
        ]
    }


@router.get("/outputs/available")
async def get_available_outputs(request: Request):
    """Tipos de output disponibles para crear."""
    from core.io_factory import OutputFactory

    return {"available_types": OutputFactory.available()}


@router.post("/outputs")
async def add_output(request: Request, body: AddOutputRequest):
    """Añade un nuevo output al pipeline en caliente y lo guarda en config.yaml."""
    ctx = _ctx(request)
    pipeline = ctx["pipeline"]

    output_type = body.type
    output_config = body.config or {}
    output_name = body.name or f"{output_type}_{int(__import__('time').time())}"

    from core.io_factory import OutputFactory

    try:
        output = OutputFactory.create(output_type, output_config)
        output.name = output_name
    except ValueError as e:
        raise HTTPException(400, str(e))

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
async def update_output(request: Request, output_name: str, body: UpdateOutputRequest):
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
        output.configure(body.config)

    if body.enabled is not None and hasattr(composite, "enable_output"):
        composite.enable_output(output_name, body.enabled)

    return {"status": "updated", "name": output_name}


@router.delete("/outputs/{output_name}")
async def remove_output(request: Request, output_name: str):
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
async def toggle_output(request: Request, output_name: str, body: dict = None):
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
