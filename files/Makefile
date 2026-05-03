.PHONY: help install test lint format type-check clean dev build pre-commit

# Variables
PYTHON := python3
PIP := pip3
POETRY := poetry
NPM := npm
NODE := node

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Mostrar esta ayuda
	@echo "$(BLUE)📚 Comandos disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(BLUE)%-20s$(NC) %s\n", $$1, $$2}'

# Backend - Python
install-python: ## Instalar dependencias Python
	@echo "$(BLUE)📦 Instalando dependencias Python...$(NC)"
	$(POETRY) install
	pre-commit install
	@echo "$(GREEN)✓ Instalación completada$(NC)"

install-npm: ## Instalar dependencias Node.js
	@echo "$(BLUE)📦 Instalando dependencias Node.js...$(NC)"
	$(NPM) install
	@echo "$(GREEN)✓ Instalación completada$(NC)"

install: install-python install-npm ## Instalar todas las dependencias

# Testing
test-backend: ## Ejecutar tests Python
	@echo "$(BLUE)🧪 Ejecutando tests Python...$(NC)"
	$(POETRY) run pytest tests/ -v --cov=src --cov-report=html --cov-report=term

test-frontend: ## Ejecutar tests TypeScript/Astro
	@echo "$(BLUE)🧪 Ejecutando tests TypeScript...$(NC)"
	$(NPM) run test

test: test-backend test-frontend ## Ejecutar todos los tests

test-coverage: ## Generar reporte de cobertura
	@echo "$(BLUE)📊 Generando reporte de cobertura...$(NC)"
	$(POETRY) run pytest tests/ --cov=src --cov-report=html
	@echo "$(GREEN)✓ Reporte generado en htmlcov/index.html$(NC)"

# Linting
lint-python: ## Lint de código Python
	@echo "$(BLUE)🔍 Linting Python...$(NC)"
	$(POETRY) run flake8 src/ tests/
	$(POETRY) run pylint src/
	@echo "$(GREEN)✓ Lint completado$(NC)"

lint-frontend: ## Lint de código TypeScript/Astro
	@echo "$(BLUE)🔍 Linting TypeScript...$(NC)"
	$(NPM) run lint
	@echo "$(GREEN)✓ Lint completado$(NC)"

lint: lint-python lint-frontend ## Lint completo

# Formatting
format-python: ## Formatear código Python
	@echo "$(BLUE)✨ Formateando Python...$(NC)"
	$(POETRY) run black src/ tests/
	$(POETRY) run isort src/ tests/
	@echo "$(GREEN)✓ Formato completado$(NC)"

format-frontend: ## Formatear código TypeScript/Astro
	@echo "$(BLUE)✨ Formateando TypeScript...$(NC)"
	$(NPM) run format
	@echo "$(GREEN)✓ Formato completado$(NC)"

format: format-python format-frontend ## Formatear todo el código

# Type checking
type-check-python: ## Verificar tipos Python
	@echo "$(BLUE)🔎 Verificando tipos Python...$(NC)"
	$(POETRY) run mypy src/
	@echo "$(GREEN)✓ Verificación completada$(NC)"

type-check-frontend: ## Verificar tipos TypeScript
	@echo "$(BLUE)🔎 Verificando tipos TypeScript...$(NC)"
	$(NPM) run type-check
	@echo "$(GREEN)✓ Verificación completada$(NC)"

type-check: type-check-python type-check-frontend ## Verificar tipos en todo el proyecto

# Development
dev-backend: ## Iniciar servidor de desarrollo Python
	@echo "$(BLUE)🚀 Iniciando backend...$(NC)"
	$(POETRY) run uvicorn src.presentation.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Iniciar servidor de desarrollo Astro
	@echo "$(BLUE)🚀 Iniciando frontend...$(NC)"
	$(NPM) run dev

dev: ## Iniciar ambos servidores (requiere dos terminales o tmux)
	@echo "$(BLUE)🚀 Para desarrollo completo, ejecutar en terminales separadas:$(NC)"
	@echo "  Terminal 1: make dev-backend"
	@echo "  Terminal 2: make dev-frontend"

# Building
build-backend: ## Build de Python
	@echo "$(BLUE)🏗️ Building Python...$(NC)"
	$(POETRY) build
	@echo "$(GREEN)✓ Build completado$(NC)"

build-frontend: ## Build de Astro
	@echo "$(BLUE)🏗️ Building Astro...$(NC)"
	$(NPM) run build
	@echo "$(GREEN)✓ Build completado$(NC)"

build: type-check lint test build-backend build-frontend ## Build completo (con checks)

# Pre-commit
pre-commit: ## Ejecutar hooks de pre-commit manualmente
	@echo "$(BLUE)🔐 Ejecutando pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)✓ Pre-commit completado$(NC)"

pre-commit-install: ## Instalar pre-commit hooks
	@echo "$(BLUE)🔐 Instalando pre-commit hooks...$(NC)"
	pre-commit install
	@echo "$(GREEN)✓ Hooks instalados$(NC)"

# Cleanup
clean: ## Limpiar archivos temporales
	@echo "$(BLUE)🧹 Limpiando archivos temporales...$(NC)"
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name dist -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name build -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .astro -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/
	@echo "$(GREEN)✓ Limpieza completada$(NC)"

clean-all: clean ## Limpiar todo incluyendo dependencias
	@echo "$(BLUE)🧹 Limpiando todo...$(NC)"
	rm -rf venv/ .venv/
	rm -rf node_modules/
	rm -f poetry.lock
	rm -f package-lock.json
	@echo "$(GREEN)✓ Limpieza total completada$(NC)"

# Database
db-migrate: ## Ejecutar migraciones de BD
	@echo "$(BLUE)🗄️ Ejecutando migraciones...$(NC)"
	$(POETRY) run alembic upgrade head
	@echo "$(GREEN)✓ Migraciones completadas$(NC)"

db-migrate-new: ## Crear nueva migración
	@echo "$(BLUE)🗄️ Creando nueva migración...$(NC)"
	$(POETRY) run alembic revision --autogenerate -m "$(msg)"
	@echo "$(GREEN)✓ Migración creada$(NC)"

db-downgrade: ## Revertir última migración
	@echo "$(BLUE)🗄️ Revirtiendo migración...$(NC)"
	$(POETRY) run alembic downgrade -1
	@echo "$(GREEN)✓ Migración revertida$(NC)"

# Security
security-check: ## Ejecutar escaneo de seguridad
	@echo "$(BLUE)🔒 Ejecutando escaneo de seguridad...$(NC)"
	$(POETRY) run bandit -r src/
	$(NPM) audit
	@echo "$(GREEN)✓ Escaneo completado$(NC)"

# Documentation
docs: ## Generar documentación
	@echo "$(BLUE)📚 Generando documentación...$(NC)"
	@echo "$(GREEN)✓ Documentación lista$(NC)"

# CI/CD simulation
ci: clean install type-check lint test ## Simular pipeline CI
	@echo "$(GREEN)✅ Pipeline CI completado exitosamente$(NC)"

.DEFAULT_GOAL := help
