# Troubleshooting macOS

> Common issues and solutions for running SRT2Web on macOS (Apple Silicon).

## Installation Issues

### `brew` not found

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Python 3.12 not found

```bash
brew install python@3.12
# or download from https://www.python.org/downloads/
```

### `pip install` fails with architecture error

If you see `"module does not support this platform"` or similar:

```bash
# Ensure you're on Apple Silicon (arm64)
uname -m
# Should output: arm64

# Use Python's built-in venv
python3.12 -m venv venv
source venv/bin/activate
```

### `onnxruntime-silicon` fails to install

```bash
# Fallback to CPU-only onnxruntime
pip install onnxruntime
```

## GPU Issues

### MPS not available

```bash
python -c "import torch; print(torch.backends.mps.is_available())"
```

If `False`:

- Ensure you're on Apple Silicon (M1/M2/M3)
- macOS 12.3+ required
- Reinstall PyTorch: `pip install torch torchvision torchaudio`

### VideoToolbox not available

```bash
ffmpeg -encoders | grep videotoolbox
```

If no results:

```bash
brew reinstall ffmpeg
```

### `nvidia-ml-py` import error

Expected on macOS (no NVIDIA GPU). The `HardwareMonitor` handles this gracefully.
Run `install_Mac.sh` which filters out `nvidia-ml-py` automatically.

## TUI Issues

### TUI doesn't launch

```bash
# Verify CLI is installed
srt2web-tui --help

# If "command not found", install CLI deps:
pip install textual httpx click rich colorama
```

### Sparklines don't render correctly

Ensure your terminal font supports Unicode block characters (U+2581–U+2588).

- **Terminal.app**: Use "Menlo" or "SF Mono" font
- **iTerm2**: Install a Nerd Font or use "Meslo NF"
- **Warp**: Built-in font works (SF Mono)

### Keyboard shortcuts don't work

- **Copy/Paste**: `Cmd+C`/`Cmd+V` should not interfere with TUI bindings (Textual handles this)
- **Quit**: Use `Q` key or `Cmd+Q`
- **Space**: Works for Start/Stop

### True color not rendering

- **Terminal.app**: Limited to 256 colors. TUI falls back automatically.
- **iTerm2**: Enable "Report terminal type" → `xterm-256color`
- **Warp**: True color supported natively.

### Mouse clicks ignored

Ensure `$TERM` is set to `xterm-256color` or similar:

```bash
export TERM=xterm-256color
srt2web-tui tui
```

## Server Issues

### Port 9999 already in use

```bash
lsof -ti :9999 | xargs kill -9
```

### FFmpeg not found

```bash
which ffmpeg || echo "not installed"
brew install ffmpeg
```

### `venv/bin/python` not found

```bash
python3.12 -m venv venv
```

## Pipeline Issues

### Pipeline starts then immediately stops

Check logs:

```bash
srt2web-tui logs --level ERROR
```

### No audio in output

Ensure audio mixer is enabled in config:

```bash
srt2web-tui config get modules.audio_mixer.enabled
```

### TTS not working

```bash
# Verify Piper model exists
ls -la models/piper/
# If empty, download voices:
python scripts/download_piper_voices.py
```

## Verification

Run the verification script to check your environment:

```bash
./init_Mac.sh
# or quick mode:
./init_Mac.sh --quick
```

---

**Need more help?** Open an issue at https://github.com/BrunoJimenez73/srt2web/issues
