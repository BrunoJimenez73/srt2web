#!/bin/bash
# init_Mac.sh - Verificacion del harness srt2web para macOS
# Equivalente funcional de init.ps1 (Windows)
# Exit code 0 = entorno listo. Exit code 1 = bloqueante.
# Usage: ./init_Mac.sh [--quick]

set -e

QUICK=false
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=true ;;
    esac
done

EXIT_CODE=0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

ok()   { echo -e "${GREEN}[OK]${NC}   $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
fail() { echo -e "${RED}[FAIL]${NC} $1"; EXIT_CODE=1; }

# ── 1. Python environment ──────────────────────────────────────────────
echo -e "\n${CYAN}--- 1. Python environment ---${NC}"

PYTHON_CMD=""
if command -v python3.12 &>/dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &>/dev/null; then
    PYVER=$(python3 --version 2>&1 | awk '{print $2}')
    case "$PYVER" in
        3.12*) PYTHON_CMD="python3" ;;
        3.13*) PYTHON_CMD="python3" ;;
        *) ;;
    esac
fi

if [ -z "$PYTHON_CMD" ]; then
    fail "Python 3.12+ not found (detected: $(python3 --version 2>&1 || echo 'none'))"
else
    ok "Python: $($PYTHON_CMD --version 2>&1)"
fi

# ── 2. Virtual environment ─────────────────────────────────────────────
echo -e "\n${CYAN}--- 2. Virtual environment ---${NC}"

if [ -d "venv" ]; then
    ok "venv directory exists"
    # Check if venv is activated
    PYTHON_BIN="venv/bin/python"
    if [ -f "$PYTHON_BIN" ]; then
        ok "venv/bin/python exists"
    else
        fail "venv/bin/python not found"
    fi
else
    fail "venv directory not found (run ./install_Mac.sh)"
fi

# ── 3. Feature list validation ─────────────────────────────────────────
echo -e "\n${CYAN}--- 3. feature_list.json ---${NC}"

if [ -f "feature_list.json" ]; then
    # Count features in_progress using python
    IN_PROGRESS=$("$PYTHON_BIN" -c "
import json
with open('feature_list.json') as f:
    data = json.load(f)
in_progress = [f for f in data['features'] if f.get('status') == 'in_progress']
print(len(in_progress))
" 2>/dev/null || echo "error")

    if [ "$IN_PROGRESS" = "error" ]; then
        fail "feature_list.json parsing failed"
    elif [ "$IN_PROGRESS" -gt 1 ]; then
        fail "feature_list.json: $IN_PROGRESS features in_progress (max 1)"
    else
        FEATURE_COUNT=$("$PYTHON_BIN" -c "
import json
with open('feature_list.json') as f:
    print(len(json.load(f)['features']))
" 2>/dev/null || echo "?")
        ok "feature_list.json valid ($FEATURE_COUNT features, $IN_PROGRESS in_progress)"
    fi
else
    fail "feature_list.json not found"
fi

# ── 4. Base files ──────────────────────────────────────────────────────
echo -e "\n${CYAN}--- 4. Base files ---${NC}"

for f in "AGENTS.md" "CHECKPOINTS.md" "feature_list.json" "progress/current.md" "progress/history.md"; do
    if [ -f "$f" ]; then
        ok "Exists $f"
    else
        fail "Missing $f"
    fi
done

# ── 5. Python dependencies ─────────────────────────────────────────────
echo -e "\n${CYAN}--- 5. Python dependencies ---${NC}"

if "$PYTHON_BIN" -m pip check &>/dev/null; then
    ok "pip check: all deps satisfied"
else
    warn "pip check: some dependencies have issues (run pip install -r config/requirements.txt)"
fi

# ── 6. Python unit tests (required) ────────────────────────────────────
echo -e "\n${CYAN}--- 6. Python unit tests ---${NC}"

PYTEST_ARGS=("-q" "--tb=short")
if [ "$QUICK" = true ]; then
    PYTEST_ARGS+=("-m" "not slow")
    warn "Quick mode: skipping slow tests (Whisper/TTS real models)"
fi

if "$PYTHON_BIN" -m pytest tests/unit/ "${PYTEST_ARGS[@]}" 2>/dev/null; then
    ok "Python unit tests: all pass"
else
    fail "Python unit tests: some tests failed"
fi

# ── 7. mypy type check (informational on Mac) ──────────────────────────
if [ "$QUICK" = false ]; then
    echo -e "\n${CYAN}--- 7. mypy type check ---${NC}"
    if "$PYTHON_BIN" -m mypy core/ server/ --strict 2>/dev/null; then
        ok "mypy: 0 errors in core/ and server/"
    else
        warn "mypy found errors (informational, not blocking)"
    fi
fi

# ── 8. Terminal capabilities (Mac-specific) ────────────────────────────
echo -e "\n${CYAN}--- 8. Terminal capabilities ---${NC}"

# Terminal detection
if [ "$TERM_PROGRAM" = "Apple_Terminal" ]; then
    ok "Terminal: Terminal.app (256 colors, limited true color)"
elif [ "$TERM_PROGRAM" = "iTerm.app" ]; then
    ok "Terminal: iTerm2 (true color ✓)"
elif [ "$TERM_PROGRAM" = "WarpTerminal" ]; then
    ok "Terminal: Warp (true color ✓)"
elif [ "$TERM_PROGRAM" = "vscode" ]; then
    ok "Terminal: VS Code integrated (true color ✓)"
else
    warn "Terminal: $TERM_PROGRAM (unknown, TUI may have limited support)"
fi

# Color depth
TERM_COLORS=$(tput colors 2>/dev/null || echo "8")
if [ "$TERM_COLORS" -ge 16777216 ]; then
    ok "True color support ($TERM_COLORS colors)"
elif [ "$TERM_COLORS" -ge 256 ]; then
    ok "256 color support ($TERM_COLORS colors)"
else
    warn "Limited color support ($TERM_COLORS colors, 256+ recommended for TUI)"
fi

# Check Unicode support (sparklines)
UNICODE_TEST=$(printf '\u2587' 2>/dev/null && echo "OK" || echo "FAIL")
if [ "$UNICODE_TEST" = "OK" ]; then
    ok "Unicode block chars supported (sparklines ✓)"
else
    warn "Unicode block chars not supported (sparklines may not render)"
fi

# Mouse support
if [ "$TERM" = "xterm-256color" ] || [ "$TERM" = "xterm-kitty" ] || [ "$TERM" = "screen-256color" ] || [ "$TERM" = "tmux-256color" ]; then
    ok "Mouse support expected (xterm protocol)"
else
    warn "Terminal type: $TERM (mouse support may be limited)"
fi

# ── Summary ────────────────────────────────────────────────────────────
echo -e "\n${CYAN}--- Summary ---${NC}"
if [ $EXIT_CODE -eq 0 ]; then
    ok "Environment ready for srt2web on macOS."
else
    fail "Blocking errors found. Review above."
fi

exit $EXIT_CODE
