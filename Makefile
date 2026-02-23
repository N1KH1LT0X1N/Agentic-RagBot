# ===========================================================================
# MediGuard AI — Makefile
# ===========================================================================
# Usage:
#   make help         — show all targets
#   make setup        — install deps + pre-commit hooks
#   make dev          — run API in dev mode with reload
#   make test         — run full test suite
#   make lint         — ruff check + mypy
#   make docker-up    — spin up all Docker services
#   make docker-down  — tear down Docker services
# ===========================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# Python / UV
PYTHON ?= python
UV     ?= uv
PIP    ?= pip

# Docker
COMPOSE := docker compose

# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
.PHONY: setup
setup: ## Install all deps (pip) + pre-commit hooks
	$(PIP) install -e ".[all]"
	pre-commit install

.PHONY: setup-uv
setup-uv: ## Install all deps with UV
	$(UV) pip install -e ".[all]"
	pre-commit install

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------
.PHONY: dev
dev: ## Run API in dev mode (auto-reload)
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

.PHONY: gradio
gradio: ## Launch Gradio web UI
	$(PYTHON) -m src.gradio_app

.PHONY: telegram
telegram: ## Start Telegram bot
	$(PYTHON) -c "from src.services.telegram.bot import MediGuardTelegramBot; MediGuardTelegramBot().run()"

# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------
.PHONY: lint
lint: ## Ruff check + MyPy
	ruff check src/ tests/
	mypy src/ --ignore-missing-imports

.PHONY: format
format: ## Ruff format
	ruff format src/ tests/
	ruff check --fix src/ tests/

.PHONY: test
test: ## Run pytest with coverage
	pytest tests/ -v --tb=short --cov=src --cov-report=term-missing

.PHONY: test-quick
test-quick: ## Run only fast unit tests
	pytest tests/ -v --tb=short -m "not slow"

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
.PHONY: docker-up
docker-up: ## Start all Docker services (detached)
	$(COMPOSE) up -d

.PHONY: docker-down
docker-down: ## Stop and remove Docker services
	$(COMPOSE) down -v

.PHONY: docker-build
docker-build: ## Build Docker images
	$(COMPOSE) build

.PHONY: docker-logs
docker-logs: ## Tail Docker logs
	$(COMPOSE) logs -f

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
.PHONY: db-upgrade
db-upgrade: ## Run Alembic migrations
	alembic upgrade head

.PHONY: db-revision
db-revision: ## Create a new Alembic migration
	alembic revision --autogenerate -m "$(msg)"

# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------
.PHONY: index-pdfs
index-pdfs: ## Parse and index all medical PDFs
	$(PYTHON) -c "\
from pathlib import Path; \
from src.services.pdf_parser.service import make_pdf_parser_service; \
from src.services.indexing.service import IndexingService; \
from src.services.embeddings.service import make_embedding_service; \
from src.services.opensearch.client import make_opensearch_client; \
parser = make_pdf_parser_service(); \
idx = IndexingService(make_embedding_service(), make_opensearch_client()); \
docs = parser.parse_directory(Path('data/medical_pdfs')); \
[idx.index_text(d.full_text, {'title': d.filename}) for d in docs if d.full_text]; \
print(f'Indexed {len(docs)} documents')"

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------
.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ *.egg-info
