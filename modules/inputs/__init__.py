"""
Input sources for SRT2Web.

Este paquete contiene las implementaciones de InputSource:
- srt_input.py: Entrada vía protocolo SRT
- file_input.py: Entrada desde archivo local
- rtmp_input.py: Entrada vía RTMP
"""

from core.io_factory import InputFactory
from modules.inputs.file_input import FileInput
from modules.inputs.rtmp_input import RTMPInput
from modules.inputs.srt_input import SRTInput

InputFactory.register("srt", SRTInput)
InputFactory.register("file", FileInput)
InputFactory.register("rtmp", RTMPInput)
