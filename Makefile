# Makefile - Unified Quality Commands for SRT2Web
# Usage: make <target> or make (defaults to help)

.PHONY: help setup test test-backend test-frontend lint type-check build clean docs

# Colors (if terminal supports it)
GREEN  := \033[0;32m
YELLOW := \033[1;33m
CYAN   := \033[0;36m
RESET  := \033[0m

help: ## Show this help message
	@echo ""
	@echo "$(CYAN)╔════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)║         SRT2Web - Unified Quality Commands             ║$(RESET)"
	@echo "$(CYAN)╚════════════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(YELLOW)Available commands:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Examples:$(RESET)"
	@echo "  make test          # Run all tests"
	@echo "  make lint          # Run all linters"
	@echo "  make ci            # Run full CI pipeline locally"
	@echo ""

# ── Setup ─────────────────────────────────────────────────────────────────────────

VENV_PY := $(if $(filter Windows_NT,$(OS)),venv\Scripts\python,venv/bin/python)

setup: ## Install all dependencies (Python + frontend)
	@echo "$(CYAN)Setting up SRT2Web...$(RESET)"
	python -m venv venv
	$(VENV_PY) -m pip install -r requirements.txt
	cd frontend && npm install
	@echo "$(GREEN)✓ Setup complete!$(RESET)"

# ── Testing ──────────────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests (pytest)
	@echo "$(CYAN)Running backend tests...$(RESET)"
	python -m pytest tests/unit/ -v --tb=short
	@echo "$(GREEN)✓ Backend tests complete!$(RESET)"

test-frontend: ## Run frontend tests (vitest)
	@echo "$(CYAN)Running frontend tests...$(RESET)"
	cd frontend && npm test -- --run
	@echo "$(GREEN)✓ Frontend tests complete!$(RESET)"

test-coverage: ## Run backend tests with coverage
	@echo "$(CYAN)Running backend tests with coverage...$(RESET)"
	python -m pytest tests/unit/ -v --cov=core --cov=modules --cov=server --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated!$(RESET)"

# ── Linting & Type Checking ────────────────────────────────────────────────────

lint: lint-python lint-frontend ## Run all linters

lint-python: ## Run Python linters (ruff)
	@echo "$(CYAN)Running Python linters...$(RESET)"
	python -m ruff check core/ modules/ server/ tests/
	@echo "$(GREEN)✓ Python linting complete!$(RESET)"

lint-frontend: ## Run frontend linter (eslint)
	@echo "$(CYAN)Running frontend linter...$(RESET)"
	cd frontend && npm run lint
	@echo "$(GREEN)✓ Frontend linting complete!$(RESET)"

type-check: type-check-python type-check-frontend ## Run all type checks

type-check-python: ## Run Python type checker (mypy)
	@echo "$(CYAN)Running Python type checker...$(RESET)"
	python -m mypy core/ server/ --config-file=pyproject.toml
	@echo "$(GREEN)✓ Python type checking complete!$(RESET)"

type-check-frontend: ## Run frontend type checker (tsc)
	@echo "$(CYAN)Running frontend type checker...$(RESET)"
	cd frontend && npx tsc --noEmit
	@echo "$(GREEN)✓ Frontend type checking complete!$(RESET)"

# ── Building ────────────────────────────────────────────────────────────────────

build: build-frontend ## Build all artifacts

build-frontend: ## Build frontend for production
	@echo "$(CYAN)Building frontend...$(RESET)"
	cd frontend && npm run build:local
	@echo "$(GREEN)✓ Frontend build complete!$(RESET)"

# ── Quality Check (CI Pipeline) ────────────────────────────────────────────────

ci: lint type-check test build ## Run full CI pipeline locally
	@echo ""
	@echo "$(CYAN)╔════════════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(CYAN)║         ✓ All quality checks passed!                      ║$(RESET)"
	@echo "$(CYAN)╚════════════════════════════════════════════════════════════╝$(RESET)"

# ── Cleaning ─────────────────────────────────────────────────────────────────────

clean: ## Clean temporary files and builds
	@echo "$(CYAN)Cleaning...$(RESET)"
	python -m pytest --cache-clear
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('*.egg-info')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('.pytest_cache')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('dist')]"
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('node_modules')]"
	python -c "import pathlib; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.pyc')]"
	python -c "import pathlib; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.pyo')]"
	python -c "import pathlib; [p.unlink(missing_ok=True) for p in pathlib.Path('.').rglob('*.egg')]"
	cd frontend && npm run clean 2>/dev/null || true
	@echo "$(GREEN)✓ Clean complete!$(RESET)"

# ── Documentation ──────────────────────────────────────────────────────────────

docs: ## Build documentation (MkDocs)
	@echo "$(CYAN)Building documentation...$(RESET)"
	cd docs && mkdocs build
	@echo "$(GREEN)✓ Documentation built!$(RESET)"

docs-serve: ## Serve documentation locally
	cd docs && mkdocs serve

# ── Security ───────────────────────────────────────────────────────────────────

security-audit: ## Run security audit on Python dependencies
	@echo "$(CYAN)Running Python security audit...$(RESET)"
	python -m pip-audit
	@echo "$(GREEN)✓ Python audit complete!$(RESET)"

security-audit-frontend: ## Run security audit on frontend dependencies
	@echo "$(CYAN)Running frontend security audit...$(RESET)"
	cd frontend && npm audit
	@echo "$(GREEN)✓ Frontend audit complete!$(RESET)"

# ── Git Hooks ───────────────────────────────────────────────────────────────────

hooks: ## Install pre-commit hooks
	@echo "$(CYAN)Installing pre-commit hooks...$(RESET)"
	python -m pip install pre-commit
	pre-commit install
	@echo "$(GREEN)✓ Pre-commit hooks installed!$(RESET)"
