import logging
from typing import TypedDict


class SubtitleEntry(TypedDict):
    start: float
    end: float
    text: str
    chunk_start: float


logger = logging.getLogger("srt2web.module.subtitle_generator")
