# Justfile - Cross-platform quality commands for SRT2Web
# Requires: just (cargo install just)

# Default task
default:
    @just --list

# ═══════════════════════════════════════════════════════
# Testing
# ═══════════════════════════════════════════════════════

# Run all backend tests
test:
    python -m pytest tests/unit/ -v

# Run tests with markers
test-unit:
    python -m pytest tests/unit/ -v -m "unit"

test-integration:
    python -m pytest tests/integration/ -v -m "integration"

test-security:
    python -m pytest tests/unit/ -v -m "security"

test-performance:
    python -m pytest tests/ -v -m "performance"

# Run specific test file
test-file file:
    python -m pytest {{file}} -v

# Run frontend tests
test-frontend:
    cd frontend && npm test

# ═══════════════════════════════════════════════════════
# Linting & Type Checking
# ═══════════════════════════════════════════════════════

# Run ruff linter
lint:
    ruff check core/ modules/ server/ tests/

# Run mypy type checker
type-check:
    mypy core/ server/ --config-file=pyproject.toml

# Run frontend type check
type-check-frontend:
    cd frontend && npx tsc --noEmit

# Run all linters
lint-all: lint type-check type-check-frontend
    @echo "All linting complete!"

# ═══════════════════════════════════════════════════════
# Building
# ═══════════════════════════════════════════════════════

# Build frontend
build-frontend:
    cd frontend && npm run build:local

# Build documentation
build-docs:
    cd docs && mkdocs build

# ═══════════════════════════════════════════════════════
# Security
# ═══════════════════════════════════════════════════════

# Run Python security audit
security-audit:
    python -m pip_audit

# Run frontend security audit
security-audit-frontend:
    cd frontend && npm audit

# ═══════════════════════════════════════════════════════
# Quality (All-in-one)
# ═══════════════════════════════════════════════════════

# Run all quality checks
quality: lint type-check test type-check-frontend test-frontend
    @echo "All quality checks passed!"

# ═══════════════════════════════════════════════════════
# Server
# ═══════════════════════════════════════════════════════

# Start server
start:
    python main.py

# Start server with live reload (development)
dev:
    python main.py --reload

# ═══════════════════════════════════════════════════════
# Cleanup
# ═══════════════════════════════════════════════════════

# Clean Python cache
clean:
    python -c "import pathlib; [p.unlink() for p in pathlib.Path('.').rglob('*.pyc')]"
    python -c "import pathlib; [p.rmdir() for p in pathlib.Path('.').rglob('__pycache__') if p.is_dir()]"

# Clean all build artifacts
clean-all: clean
    rm -rf frontend/dist/
    rm -rf docs/site/
    rm -rf temp/
    rm -rf venv/

# ═══════════════════════════════════════════════════════
# Information
# ═══════════════════════════════════════════════════════

# Show project info
info:
    @echo "SRT2Web - Real-time Subtitle Translation Pipeline"
    @echo "Version: $$(python -c "import yaml; print(yaml.safe_load(open('config.yaml'))['version'])")"
    @echo "Python: $$(python --version)"
    @echo "Node: $$(node --version)"
    @echo "FFmpeg: $$(ffmpeg -version | head -n1)"

# Show test coverage
coverage:
    python -m pytest tests/unit/ --cov=core --cov=modules --cov=server --cov-report=term-missing
