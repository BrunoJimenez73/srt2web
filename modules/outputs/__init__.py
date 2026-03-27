"""
Output sinks for SRT2Web.

Este paquete contiene las implementaciones de OutputSink:
- hls_output.py: Salida vía HLS para navegador web
- rtmp_output.py: Salida vía RTMP
"""

from core.io_factory import OutputFactory

from modules.outputs.hls_output import HLSOutput
from modules.outputs.rtmp_output import RTMPOutput

OutputFactory.register("hls", HLSOutput)
OutputFactory.register("rtmp", RTMPOutput)
