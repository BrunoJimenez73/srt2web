#!/usr/bin/env just

# justfile - Unified Quality Commands for SRT2Web
# Usage: just <command> or just (defaults to help)

# Default task
default: help

# ── Setup ──────────────────────────────────────────────────────────────────────

setup:
    @echo "Setting up SRT2Web..."
    python -m venv venv
    venv/Scripts/python.exe -m pip install -r requirements.txt
    cd frontend && npm install
    @echo "✓ Setup complete!"

# ── Testing ────────────────────────────────────────────────────────────────────

test: test-backend test-frontend

test-backend:
    @echo "Running backend tests..."
    python -m pytest tests/unit/ -v --tb=short
    @echo "✓ Backend tests complete!"

test-frontend:
    @echo "Running frontend tests..."
    cd frontend && npm test -- --run
    @echo "✓ Frontend tests complete!"

test-coverage:
    @echo "Running backend tests with coverage..."
    python -m pytest tests/unit/ -v --cov=core --cov=modules --cov=server --cov-report=term-missing
    @echo "✓ Coverage report generated!"

# ── Linting & Type Checking ─────────────────────────────────────────────────

lint: lint-python lint-frontend

lint-python:
    @echo "Running Python linters..."
    python -m ruff check core/ modules/ server/ tests/
    @echo "✓ Python linting complete!"

lint-frontend:
    @echo "Running frontend linter..."
    cd frontend && npm run lint
    @echo "✓ Frontend linting complete!"

type-check: type-check-python type-check-frontend

type-check-python:
    @echo "Running Python type checker..."
    python -m mypy core/ server/ --config-file=pyproject.toml
    @echo "✓ Python type checking complete!"

type-check-frontend:
    @echo "Running frontend type checker..."
    cd frontend && npx tsc --noEmit
    @echo "✓ Frontend type checking complete!"

# ── Building ─────────────────────────────────────────────────────────────────────

build: build-frontend

build-frontend:
    @echo "Building frontend..."
    cd frontend && npm run build:local
    @echo "✓ Frontend build complete!"

# ── Quality Check (CI Pipeline) ──────────────────────────────────────────────

ci: lint type-check test build
    @echo ""
    @echo "╔══════════════════════════════════════════════════════════════╗"
    @echo "║         ✓ All quality checks passed!                      ║"
    @echo "╚══════════════════════════════════════════════════════════════╝"

# ── Cleaning ──────────────────────────────────────────────────────────────────────

clean:
    @echo "Cleaning..."
    python -m pytest --cache-clear
    rm -rf **/__pycache__
    rm -rf **/*.egg-info
    rm -rf **/.pytest_cache
    rm -rf **/node_modules
    rm -rf **/*.pyc
    rm -rf **/*.pyo
    rm -rf **/*.egg
    cd frontend && npm run clean 2>/dev/null || true
    @echo "✓ Clean complete!"

# ── Documentation ──────────────────────────────────────────────────────────────

docs:
    @echo "Building documentation..."
    cd docs && mkdocs build
    @echo "✓ Documentation built!"

docs-serve:
    cd docs && mkdocs serve

# ── Security ──────────────────────────────────────────────────────────────────────

security-audit:
    @echo "Running Python security audit..."
    python -m pip-audit
    @echo "✓ Python audit complete!"

security-audit-frontend:
    @echo "Running frontend security audit..."
    cd frontend && npm audit
    @echo "✓ Frontend audit complete!"

# ── Git Hooks ──────────────────────────────────────────────────────────────────────

hooks:
    @echo "Installing pre-commit hooks..."
    python -m pip install pre-commit
    pre-commit install
    @echo "✓ Pre-commit hooks installed!"
