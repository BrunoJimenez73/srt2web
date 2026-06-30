def format_timestamp(seconds: float, format_type: str = "vtt") -> str:
    """Convert float seconds to VTT (HH:MM:SS.mmm) or SRT (HH:MM:SS,mmm) timestamp."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)

    if format_type == "srt":
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
