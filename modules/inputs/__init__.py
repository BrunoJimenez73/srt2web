"""
Input sources for SRT2Web.

Este paquete contiene las implementaciones de InputSource:
- srt_input.py: Entrada vía protocolo SRT
- file_input.py: Entrada desde archivo local
- rtmp_input.py: Entrada vía RTMP (futuro)
- audio_input.py: Entrada de solo audio (futuro)
"""

from core.io_factory import InputFactory

# Importar todas las implementaciones para auto-registro
from modules.inputs.srt_input import SRTInput
from modules.inputs.file_input import FileInput
