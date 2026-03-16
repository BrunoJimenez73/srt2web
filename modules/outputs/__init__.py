"""
Output sinks for SRT2Web.

Este paquete contiene las implementaciones de OutputSink:
- hls_output.py: Salida vía HLS para navegador web
- srt_output.py: Salida vía protocolo SRT (futuro)
- rtmp_output.py: Salida vía RTMP (futuro)
"""

from core.io_factory import OutputFactory

# Importar todas las implementaciones para auto-registro
from modules.outputs.hls_output import HLSOutput
