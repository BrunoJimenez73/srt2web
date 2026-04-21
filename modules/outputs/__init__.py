"""
Output sinks for SRT2Web.

Este paquete contiene las implementaciones de OutputSink:
- hls_output.py: Salida vía HLS para navegador web
- rtmp_output.py: Salida vía RTMP
- recording_output.py: Grabación continua a archivo
- file_output.py: Salida a archivos locales (chunks)
- srt_output.py: Salida vía protocolo SRT
- webrtc_output.py: Salida vía WebRTC
"""

from core.io_factory import OutputFactory

from modules.outputs.hls_output import HLSOutput
from modules.outputs.rtmp_output import RTMPOutput
from modules.outputs.recording_output import RecordingOutput
from modules.outputs.file_output import FileOutput
from modules.outputs.srt_output import SRTOutput
from modules.outputs.webrtc_output import WebRTCOutput

OutputFactory.register("webplayer", HLSOutput)
OutputFactory.register("web", HLSOutput)
OutputFactory.register("hls", HLSOutput)
OutputFactory.register("rtmp", RTMPOutput)
OutputFactory.register("recording", RecordingOutput)
OutputFactory.register("file", FileOutput)
OutputFactory.register("srt", SRTOutput)
OutputFactory.register("webrtc", WebRTCOutput)
