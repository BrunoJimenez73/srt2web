"""
Piper TTS Model Loader - Subprocess-based loading to avoid blocking the main event loop.

This module runs Piper model loading in a separate Python process,
which completely avoids the GIL and daemon thread issues.
"""

import os
import sys
import json
import subprocess
import time
import logging

logger = logging.getLogger("srt2web.module.tts_engine")

# The script that will run in the subprocess
LOADER_SCRIPT = '''
import sys
import os
import json
import warnings

def main():
    """Load Piper model and report results."""
    try:
        voice_name = sys.argv[1]
        model_path = sys.argv[2]
        config_path = sys.argv[3]
        device = sys.argv[4]  # "auto", "cuda", or "cpu"
        
        # Import piper and onnxruntime
        from piper import PiperVoice
        import onnxruntime
        
        print(f"[PIPER_DEBUG] Python: {sys.version}", file=sys.stderr)
        print(f"[PIPER_DEBUG] ONNX Runtime: {onnxruntime.__version__}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Available providers: {onnxruntime.get_available_providers()}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Model path: {model_path}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Config path: {config_path}", file=sys.stderr)
        print(f"[PIPER_DEBUG] Device requested: {device}", file=sys.stderr)
        
        # Check CUDA availability
        cuda_available = "CUDAExecutionProvider" in onnxruntime.get_available_providers()
        print(f"[PIPER_DEBUG] CUDA available: {cuda_available}", file=sys.stderr)
        
        use_cuda = False
        voice = None
        
        # Try to load with CUDA if available and requested
        if device == "cuda" or (device == "auto" and cuda_available):
            if cuda_available:
                try:
                    print(f"[PIPER_DEBUG] Attempting to load with CUDA...", file=sys.stderr)
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        voice = PiperVoice.load(model_path, config_path, use_cuda=True)
                    use_cuda = True
                    print(f"[PIPER_DEBUG] Successfully loaded with CUDA", file=sys.stderr)
                except Exception as e:
                    print(f"[PIPER_DEBUG] CUDA load failed: {e}", file=sys.stderr)
                    voice = None
            else:
                print(f"[PIPER_DEBUG] CUDA requested but not available", file=sys.stderr)
        
        # Load with CPU if CUDA failed or was not requested
        if voice is None:
            print(f"[PIPER_DEBUG] Loading with CPU...", file=sys.stderr)
            voice = PiperVoice.load(model_path, config_path, use_cuda=False)
            use_cuda = False
            print(f"[PIPER_DEBUG] Successfully loaded with CPU", file=sys.stderr)
        
        # Report sample rate
        print(f"[PIPER_DEBUG] Sample rate: {voice.config.sample_rate}", file=sys.stderr)
        
        # Success - output JSON result to stdout
        result = {
            "status": "success",
            "using_cuda": use_cuda,
            "sample_rate": voice.config.sample_rate,
            "provider": "CUDAExecutionProvider" if use_cuda else "CPUExecutionProvider"
        }
        print(json.dumps(result))
        
    except ImportError as e:
        result = {"status": "error", "error": f"Import error: {e}"}
        print(json.dumps(result))
        sys.exit(1)
    except Exception as e:
        result = {"status": "error", "error": str(e)}
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    main()
'''


def load_piper_model_subprocess(
    voice_name: str,
    model_path: str,
    config_path: str,
    device: str = "auto",
    timeout: int = 90
) -> dict:
    """
    Load Piper model in a subprocess.
    
    Returns:
        dict with keys: status, using_cuda, sample_rate, provider, error (if failed)
    """
    start_time = time.time()
    
    # Create a temporary script file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
        f.write(LOADER_SCRIPT)
        script_path = f.name
    
    try:
        logger.info(f"[PIPER_DEBUG] Starting subprocess loader for {voice_name}")
        logger.info(f"[PIPER_DEBUG] Timeout: {timeout}s, Device: {device}")
        
        # Add CUDA/cuDNN paths to subprocess environment
        import site
        env = os.environ.copy()
        
        # ONLY use project's local CUDA bin directory (CUDA 12.4 + cuDNN 8.x)
        # Do NOT use system CUDA 13.2 to avoid conflicts
        cuda_paths = []
        
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_cuda_bin = os.path.join(project_dir, "bin", "cuda")
        if os.path.exists(project_cuda_bin):
            cuda_paths.append(project_cuda_bin)
            logger.info(f"[PIPER_DEBUG] Using ONLY project CUDA: {project_cuda_bin}")
        
        # Do NOT add System32 or CUDA Toolkit paths to avoid loading CUDA 13.2 DLLs
        
        # Add CUDA paths to front of PATH
        if cuda_paths:
            env["PATH"] = os.pathsep.join(cuda_paths) + os.pathsep + env.get("PATH", "")
            logger.info(f"[PIPER_DEBUG] CUDA paths set to: {cuda_paths}")
        
        # Run the subprocess
        result = subprocess.run(
            [sys.executable, script_path, voice_name, model_path, config_path, device],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env
        )
        
        elapsed = time.time() - start_time
        logger.info(f"[PIPER_DEBUG] Subprocess finished after {elapsed:.1f}s")
        
        # Parse stderr for debug info
        stderr_lines = []
        if result.stderr:
            for line in result.stderr.strip().split('\n'):
                if line.strip():
                    stderr_lines.append(line.strip())
                    logger.info(f"[PIPER_DEBUG] {line.strip()}")
        
        # Check for CUDA dependency errors
        cuda_error_detected = False
        for line in stderr_lines:
            if "cublas" in line.lower() or "cudnn" in line.lower():
                cuda_error_detected = True
                logger.warning(f"[PIPER_DEBUG] CUDA dependency missing - consider installing CUDA Toolkit 12.x and cuDNN 9.x")
        
        # Check return code
        if result.returncode != 0:
            logger.error(f"[PIPER_DEBUG] Subprocess failed with code {result.returncode}")
            if result.stdout:
                logger.error(f"[PIPER_DEBUG] stdout: {result.stdout}")
            
            error_msg = f"Process exited with code {result.returncode}"
            if cuda_error_detected:
                error_msg += " (CUDA dependencies missing - using CPU instead)"
            return {"status": "error", "error": error_msg}
        
        # Parse JSON result from stdout (handle extra output before JSON)
        try:
            stdout = result.stdout.strip()
            # Find JSON in stdout (may have EP errors before it)
            json_start = stdout.find('{')
            if json_start >= 0:
                json_str = stdout[json_start:]
                data = json.loads(json_str)
            else:
                data = json.loads(stdout)
            logger.info(f"[PIPER_DEBUG] Load result: {data}")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"[PIPER_DEBUG] Failed to parse JSON: {e}")
            logger.error(f"[PIPER_DEBUG] stdout was: {result.stdout}")
            return {"status": "error", "error": f"Failed to parse result: {e}"}
            
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        logger.error(f"[PIPER_DEBUG] Subprocess timed out after {elapsed:.1f}s (limit: {timeout}s)")
        return {"status": "error", "error": f"Loading timed out after {timeout} seconds"}
    except Exception as e:
        logger.error(f"[PIPER_DEBUG] Unexpected error: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        # Clean up temp script
        try:
            os.unlink(script_path)
        except OSError:
            pass


def check_piper_environment() -> dict:
    """Check if piper and onnxruntime are available, report versions."""
    result = {
        "piper_available": False,
        "onnxruntime_available": False,
        "onnx_version": None,
        "providers": [],
        "cuda_available": False,
        "python_path": sys.executable,
        "python_version": sys.version
    }
    
    try:
        import piper
        result["piper_available"] = True
    except ImportError as e:
        result["piper_error"] = str(e)
    
    try:
        import onnxruntime as ort
        result["onnxruntime_available"] = True
        result["onnx_version"] = ort.__version__
        result["providers"] = ort.get_available_providers()
        result["cuda_available"] = "CUDAExecutionProvider" in result["providers"]
    except ImportError as e:
        result["onnx_error"] = str(e)
    
    return result
