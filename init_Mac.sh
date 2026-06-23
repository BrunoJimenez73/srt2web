#!/bin/bash
# init_Mac.sh - Verificacion del harness srt2web para macOS
# Equivalente funcional de init.ps1 (Windows)
# Exit code 0 = entorno listo. Exit code 1 = bloqueante.
# Usage: ./init_Mac.sh [--quick]

# Not using set -e: this is a verification script, failures are handled explicitly
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

# ── 3. Feature tracking (harness.db) ──────────────────────────────────
echo -e "\n${CYAN}--- 3. Feature tracking (harness.db) ---${NC}"

if [ -f "harness.db" ]; then
    if "$PYTHON_BIN" -m harness health 2>/dev/null; then
        ok "harness.db: healthy"
    else
        fail "harness.db: issues detected"
    fi
else
    warn "harness.db not found — migrating from feature_list.json"
    if "$PYTHON_BIN" -m harness migrate 2>/dev/null; then
        ok "harness.db created via migration"
    else
        fail "Migration failed"
    fi
fi

# Legacy JSON validation
if [ -f "feature_list.json" ]; then
    FEATURE_COUNT=$("$PYTHON_BIN" -c "
import json
with open('feature_list.json') as f:
    print(len(json.load(f)['features']))
" 2>/dev/null || echo "?")
    ok "feature_list.json exists ($FEATURE_COUNT features, legacy)"
else
    warn "feature_list.json not found (using harness.db)"
fi

# ── 4. Base files ──────────────────────────────────────────────────────
echo -e "\n${CYAN}--- 4. Base files ---${NC}"

for f in "AGENTS.md" "CHECKPOINTS.md" "feature_list.json"; do
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
    PYTEST_ARGS+=("-m" "not slow" "-n" "auto" "--basetemp" "./tmpsrt2web-pytest")
    warn "Quick mode: skipping slow tests (Whisper/TTS real models)"
fi

if "$PYTHON_BIN" -m pytest tests/unit/ "${PYTEST_ARGS[@]}" 2>/dev/null; then
    ok "Python unit tests: all pass"
else
    fail "Python unit tests: some tests failed"
fi

# ── 7. mypy type check ─────────────────────────────────────────────────
echo -e "\n${CYAN}--- 7. mypy type check ---${NC}"
if "$PYTHON_BIN" -m mypy core/ server/ modules/ --config-file pyproject.toml 2>/dev/null; then
    ok "mypy: 0 errors in core/, server/ and modules/"
else
    if [ "$QUICK" = true ]; then
        warn "mypy found errors (informational in quick mode)"
    else
        fail "mypy found errors"
    fi
fi

# ── 8. TypeScript check (required) ─────────────────────────────────────
echo -e "\n${CYAN}--- 8. TypeScript (required) ---${NC}"
if [ -f "frontend/node_modules/.bin/tsc" ]; then
    ASTRO_TELEMETRY_DISABLED=1 frontend/node_modules/.bin/tsc --noEmit 2>/dev/null && ok "TypeScript: 0 errors" || fail "TypeScript has errors"
elif command -v npx &>/dev/null; then
    (cd frontend && ASTRO_TELEMETRY_DISABLED=1 npx tsc --noEmit 2>/dev/null) && ok "TypeScript: 0 errors" || fail "TypeScript has errors"
else
    fail "TypeScript compiler not found (frontend/node_modules/.bin/tsc or npx)"
fi

# ── 9. Frontend tests (required in quick, informational in full) ───────
echo -e "\n${CYAN}--- 9. Frontend tests ---${NC}"
if [ -f "frontend/node_modules/.bin/vitest" ]; then
    ASTRO_TELEMETRY_DISABLED=1 frontend/node_modules/.bin/vitest run 2>/dev/null && ok "Frontend tests: pass" || warn "Frontend tests: some failed (non-blocking in quick mode)"
elif command -v npm &>/dev/null; then
    (cd frontend && ASTRO_TELEMETRY_DISABLED=1 npm test 2>/dev/null) && ok "Frontend tests: pass" || warn "Frontend tests: some failed (non-blocking in quick mode)"
else
    warn "npm not available (cannot run frontend tests)"
fi

if [ "$QUICK" = false ]; then
    # ── 9b. Build frontend (informational) ──────────────────────────────
    echo -e "\n${CYAN}--- 9b. Build frontend (informational) ---${NC}"
    if [ -f "frontend/node_modules/.bin/astro" ]; then
        (cd frontend && ASTRO_TELEMETRY_DISABLED=1 npm run build:local 2>/dev/null) && ok "Frontend build: success" || warn "Frontend build: failed (non-blocking)"
    else
        warn "Astro not available (frontend/node_modules/.bin/astro)"
    fi
fi

# ── 10. Tooling check ──────────────────────────────────────────────────
echo -e "\n${CYAN}--- 10. Tooling check ---${NC}"
if "$PYTHON_BIN" -c "import ruff" 2>/dev/null; then
    ok "ruff available"
else
    warn "ruff not installed (run: pip install ruff)"
fi
if "$PYTHON_BIN" -c "import mkdocs" 2>/dev/null; then
    ok "mkdocs available"
else
    warn "mkdocs not installed (run: pip install mkdocs)"
fi

# ── 11. Terminal capabilities (Mac-specific) ───────────────────────────
echo -e "\n${CYAN}--- 11. Terminal capabilities ---${NC}"

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
