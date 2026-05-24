"""Piper TTS one-shot loader — validates model in a short-lived subprocess.

Usage: python -m modules.piper_loader_script <voice_name> <model_path> <config_path> <device>
"""

import json
import sys
import warnings


def main() -> None:
    try:
        voice_name = sys.argv[1]
        model_path = sys.argv[2]
        config_path = sys.argv[3]
        device = sys.argv[4]

        import onnxruntime
        from piper import PiperVoice

        print(f"[PIPER_DEBUG] Python: {sys.version}", file=sys.stderr)
        print(f"[PIPER_DEBUG] ONNX Runtime: {onnxruntime.__version__}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Available providers: {onnxruntime.get_available_providers()}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Model path: {model_path}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Config path: {config_path}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Device requested: {device}", file=sys.stderr)

        cuda_available = "CUDAExecutionProvider" in onnxruntime.get_available_providers()
        print(f"[PIPER_DEBUG] CUDA available: {cuda_available}", file=sys.stderr)

        use_cuda = False
        voice = None

        if device == "cuda" or (device == "auto" and cuda_available) and cuda_available:
            try:
                print("[PIPER_DEBUG] Attempting to load with CUDA...", file=sys.stderr)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    voice = PiperVoice.load(model_path, config_path, use_cuda=True)
                use_cuda = True
                print("[PIPER_DEBUG] Successfully loaded with CUDA", file=sys.stderr)
            except Exception as e:
                print(f"[PIPER_DEBUG] CUDA load failed: {e}", file=sys.stderr)
                voice = None

        if voice is None:
            print("[PIPER_DEBUG] Loading with CPU...", file=sys.stderr)
            voice = PiperVoice.load(model_path, config_path, use_cuda=False)
            print("[PIPER_DEBUG] Successfully loaded with CPU", file=sys.stderr)

        print(f"[PIPER_DEBUG] Sample rate: {voice.config.sample_rate}", file=sys.stderr)

        result = {
            "status": "success",
            "using_cuda": use_cuda,
            "sample_rate": voice.config.sample_rate,
            "provider": "CUDAExecutionProvider" if use_cuda else "CPUExecutionProvider",
        }
        print(json.dumps(result))

    except ImportError as e:
        print(json.dumps({"status": "error", "error": f"Import error: {e}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
