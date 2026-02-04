# =============================================================================
# NESTSECURE - Makefile
# =============================================================================
# Comandos útiles para desarrollo
# =============================================================================

.PHONY: help install dev test lint clean docker-up docker-down docker-logs

# Variables
# Usar "docker compose" (nuevo) en lugar de "docker-compose" (deprecated)
DOCKER_COMPOSE_DEV = docker compose -f docker-compose.dev.yml
PYTHON = python
PIP = pip

# Color codes para output
GREEN = \033[0;32m
YELLOW = \033[0;33m
NC = \033[0m # No Color

help: ## Muestra esta ayuda
	@echo "$(GREEN)NestSecure - Comandos Disponibles$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Desarrollo Local
# =============================================================================

install: ## Instala dependencias del backend
	@echo "$(GREEN)Instalando dependencias...$(NC)"
	cd backend && $(PIP) install -r requirements-dev.txt

dev: ## Ejecuta el servidor de desarrollo (sin Docker)
	@echo "$(GREEN)Iniciando servidor de desarrollo...$(NC)"
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test: ## Ejecuta todos los tests
	@echo "$(GREEN)Ejecutando tests...$(NC)"
	cd backend && pytest -v

test-cov: ## Ejecuta tests con coverage
	@echo "$(GREEN)Ejecutando tests con coverage...$(NC)"
	cd backend && pytest --cov=app --cov-report=html --cov-report=term-missing

test-health: ## Ejecuta solo tests de health endpoints
	@echo "$(GREEN)Ejecutando tests de health...$(NC)"
	cd backend && pytest app/tests/test_api/test_health.py -v

test-config: ## Ejecuta solo tests de configuración
	@echo "$(GREEN)Ejecutando tests de config...$(NC)"
	cd backend && pytest app/tests/test_config.py -v

lint: ## Ejecuta linters (ruff)
	@echo "$(GREEN)Ejecutando linters...$(NC)"
	cd backend && ruff check app/
	cd backend && ruff format --check app/

lint-fix: ## Corrige errores de lint automáticamente
	@echo "$(GREEN)Corrigiendo errores de lint...$(NC)"
	cd backend && ruff check --fix app/
	cd backend && ruff format app/

# =============================================================================
# Docker
# =============================================================================

docker-up: ## Levanta todos los servicios con Docker
	@echo "$(GREEN)Levantando servicios...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d

docker-up-build: ## Levanta servicios reconstruyendo imágenes
	@echo "$(GREEN)Levantando servicios (rebuild)...$(NC)"
	$(DOCKER_COMPOSE_DEV) up -d --build

docker-down: ## Detiene todos los servicios
	@echo "$(GREEN)Deteniendo servicios...$(NC)"
	$(DOCKER_COMPOSE_DEV) down

docker-logs: ## Muestra logs de todos los servicios
	$(DOCKER_COMPOSE_DEV) logs -f

docker-logs-backend: ## Muestra logs solo del backend
	$(DOCKER_COMPOSE_DEV) logs -f backend

docker-logs-frontend: ## Muestra logs solo del frontend
	$(DOCKER_COMPOSE_DEV) logs -f frontend

docker-build: ## Reconstruye las imágenes Docker
	@echo "$(GREEN)Reconstruyendo imágenes...$(NC)"
	$(DOCKER_COMPOSE_DEV) build

docker-build-frontend: ## Reconstruye solo la imagen del frontend
	@echo "$(GREEN)Reconstruyendo imagen del frontend...$(NC)"
	$(DOCKER_COMPOSE_DEV) build frontend

docker-restart: ## Reinicia todos los servicios
	@echo "$(GREEN)Reiniciando servicios...$(NC)"
	$(DOCKER_COMPOSE_DEV) restart

docker-restart-frontend: ## Reinicia solo el frontend
	@echo "$(GREEN)Reiniciando frontend...$(NC)"
	$(DOCKER_COMPOSE_DEV) restart frontend

docker-ps: ## Muestra estado de los contenedores
	$(DOCKER_COMPOSE_DEV) ps

docker-shell-backend: ## Abre shell en el contenedor del backend
	$(DOCKER_COMPOSE_DEV) exec backend /bin/bash

docker-shell-frontend: ## Abre shell en el contenedor del frontend
	$(DOCKER_COMPOSE_DEV) exec frontend /bin/sh

docker-shell-db: ## Abre psql en el contenedor de PostgreSQL
	$(DOCKER_COMPOSE_DEV) exec postgres psql -U nestsecure -d nestsecure_db

# =============================================================================
# Base de Datos
# =============================================================================

db-migrate: ## Ejecuta migraciones de Alembic
	@echo "$(GREEN)Ejecutando migraciones...$(NC)"
	cd backend && alembic upgrade head

db-migrate-new: ## Crea nueva migración (usar: make db-migrate-new MSG="descripcion")
	@echo "$(GREEN)Creando migración: $(MSG)$(NC)"
	cd backend && alembic revision --autogenerate -m "$(MSG)"

db-downgrade: ## Revierte última migración
	@echo "$(YELLOW)Revirtiendo última migración...$(NC)"
	cd backend && alembic downgrade -1

db-reset: ## Elimina y recrea la base de datos (CUIDADO!)
	@echo "$(YELLOW)⚠️  Eliminando base de datos...$(NC)"
	$(DOCKER_COMPOSE_DEV) down -v
	$(DOCKER_COMPOSE_DEV) up -d postgres redis
	@echo "$(GREEN)Esperando que PostgreSQL esté listo...$(NC)"
	sleep 10
	make db-migrate

# =============================================================================
# Utilidades
# =============================================================================

clean: ## Limpia archivos temporales
	@echo "$(GREEN)Limpiando archivos temporales...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Limpieza completada$(NC)"

health: ## Verifica health de la API
	@echo "$(GREEN)Verificando health...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API no disponible"

health-ready: ## Verifica readiness de la API
	@echo "$(GREEN)Verificando readiness...$(NC)"
	@curl -s http://localhost:8000/health/ready | python -m json.tool || echo "API no disponible"

# =============================================================================
# Setup Inicial
# =============================================================================

setup: ## Setup inicial del proyecto
	@echo "$(GREEN)Configurando proyecto NestSecure...$(NC)"
	@echo ""
	@echo "1. Copiando archivo de entorno..."
	cp backend/.env.example backend/.env 2>/dev/null || true
	@echo "2. Instalando dependencias..."
	make install
	@echo ""
	@echo "$(GREEN)✓ Setup completado!$(NC)"
	@echo ""
	@echo "Próximos pasos:"
	@echo "  1. Edita backend/.env con tus configuraciones"
	@echo "  2. Ejecuta: make docker-up"
	@echo "  3. Verifica: make health"
