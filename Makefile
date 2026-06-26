.DEFAULT_GOAL := help
.PHONY: help install install-all install-dev lint format test test-cov \
        run-ui run-pipeline dry-run \
        docker-build docker-up docker-up-obs docker-up-lineage docker-up-all docker-down docker-logs \
        clean

PYTHON     := python
UV         := uv
COMPOSE    := docker compose

EXTRAS     ?= ui,observability
PIPELINE   ?= examples/eonet_events.yaml

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}' | sort

# ── Install ───────────────────────────────────────────────────────────────────

install: ## Install core dependencies only
	$(UV) sync

install-all: ## Install all optional extras
	$(UV) sync --all-extras

install-dev: ## Install dev dependencies (tests + linting)
	$(UV) sync --group dev

# ── Lint & format ─────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	$(UV) run ruff check maestro/ tests/

format: ## Auto-format with ruff
	$(UV) run ruff format maestro/ tests/

# ── Tests ─────────────────────────────────────────────────────────────────────

test: ## Run test suite
	$(UV) run pytest tests/ -v

test-cov: ## Run tests with coverage report
	$(UV) run pytest tests/ -v --cov=maestro --cov-report=term-missing --cov-report=html

test-fast: ## Run tests in parallel (requires pytest-xdist)
	$(UV) run pytest tests/ -v -n auto

# ── Run locally ───────────────────────────────────────────────────────────────

run-ui: ## Start the FastAPI management UI (http://localhost:8080)
	$(UV) run python -m maestro.ui

run-pipeline: ## Run a pipeline YAML (PIPELINE=path/to/spec.yaml)
	$(UV) run python -c "from maestro.main import run; run('$(PIPELINE)')"

dry-run: ## Dry-run a pipeline without executing transforms (PIPELINE=path/to/spec.yaml)
	$(UV) run python -c "from maestro.pipeline.dryrun import dry_run; dry_run('$(PIPELINE)')"

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build: ## Build the Docker image (EXTRAS=ui,observability)
	docker build --build-arg EXTRAS=$(EXTRAS) -t maestro:local .

docker-up: ## Start only the UI container
	$(COMPOSE) --profile ui up -d

docker-up-obs: ## Start UI + Prometheus + Grafana
	$(COMPOSE) --profile ui --profile observability up -d

docker-up-lineage: ## Start UI + Marquez lineage services
	$(COMPOSE) --profile ui --profile lineage up -d

docker-up-all: ## Start all profiles (UI + observability + lineage)
	$(COMPOSE) --profile ui --profile observability --profile lineage up -d

docker-down: ## Stop and remove all containers
	$(COMPOSE) --profile ui --profile observability --profile lineage down

docker-logs: ## Tail logs for all running containers
	$(COMPOSE) logs -f


# ── Clean ─────────────────────────────────────────────────────────────────────

clean: ## Remove build artefacts, caches, and coverage reports
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name ".coverage" -delete
