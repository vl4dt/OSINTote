# OSINTote — dev workflow via uv
# Usage: make <target>

SHELL := /bin/bash

.PHONY: all dev fmt lint check test test-cov build help init

help: ## Show this help
	@grep -E '^[a-zA-Z._-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

init: ## Bootstrap dev environment with uv sync
	@uv sync --all-groups

dev: ## Run dev servers (Python API + frontend)
	@echo "Starting OSINTote dev servers..."
	@uv run uvicorn osintote.api.app:app --reload --host 0.0.0.0 --port 8000 & \
		uv -C frontend run dev

dev-both: ## Start backend and frontend in one terminal (cross-platform)
	@echo "Starting OSINTote (backend + frontend)..."
	@echo "  Backend  → http://127.0.0.1:8000"
	@echo "  Frontend → http://localhost:5173"
	@echo "  API docs → http://127.0.0.1:8000/api/docs"
	@echo ""
	@uv run uvicorn osintote.api.app:app --reload --host 0.0.0.0 --port 8000 &
	@uv -C frontend run dev

fmt: ## Format Python and frontend code
	@uv run ruff format src/osintote
	@uv -C frontend run format

lint: ## Lint and type-check Python
	@uv run ruff check src/osintote
	@uv run mypy --ignore-missing-imports src/osintote

check: lint ## Run all checks (lint + type-check)

test: ## Run tests
	@uv run pytest src/

test-cov: ## Run tests with coverage report
	@uv run coverage run -m pytest src/
	@uv run coverage report --show-missing
	@uv run coverage html

build: ## Build Python package
	@uv build

clean: ## Remove build artifacts
	@rm -rf dist/ build/ *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@rm -f .coverage htmlcov/*
	@echo "Cleaned."

migrate: ## Run Alembic migrations
	@uv run alembic upgrade head

seed: ## Seed the database with initial data
	@uv run python -c "from osintote.db.seed import seed_db; seed_db()"

.PHONY: help init dev fmt lint check test test-cov build clean migrate seed
