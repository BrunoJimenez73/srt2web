def check():
    print("Checking dependencies...")
    try:
        import faster_whisper

        print("✓ faster-whisper ok")
    except ImportError:
        print("✗ faster-whisper missing")

    try:
        import argostranslate

        print("✓ argostranslate ok")
    except ImportError:
        print("✗ argostranslate missing")

    try:
        import edge_tts

        print("✓ edge-tts ok")
    except ImportError:
        print("✗ edge-tts missing")

    try:
        import piper

        print("✓ piper ok")
    except ImportError:
        print("✗ piper missing")

    try:
        import torch

        print(f"✓ torch ok (CUDA: {torch.cuda.is_available()})")
    except ImportError:
        print("✗ torch missing")


if __name__ == "__main__":
    check()
