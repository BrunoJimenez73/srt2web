import logging
from typing import TypedDict


class SubtitleEntry(TypedDict):
    start: float
    end: float
    text: str
    chunk_start: float


class HLSFragment(TypedDict):
    chunk_index: int
    duration: float
    start: float
    path: str


logger = logging.getLogger("srt2web.module.subtitle_generator")
