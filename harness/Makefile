.PHONY: demo up load verify down clean

# Overridable workload:  make demo TRANSFERS=100 ORDERS=40 SPREAD=90
# SPREAD = seconds to pace the starts over, so rate()/APS is measurable (0 = burst).
TRANSFERS ?= 50
ORDERS    ?= 25
SPREAD    ?= 60
export TRANSFERS ORDERS SPREAD

COMPOSE = docker compose -f cluster/docker-compose.yml

# Load harness/.env if present (Datadog keys etc.) so you don't have to `export`.
# Copy .env.example -> .env to get started. Values also flow to docker compose below.
-include .env

# Datadog lane is opt-in and automatic: set DD_API_KEY (+ DD_APP_KEY to query back) and
# the agent container starts alongside the cluster and verify.sh reconciles the real
# Datadog query. Unset, everything runs offline exactly as before.
DD_PROFILE := $(if $(DD_API_KEY),--profile datadog,)
export DD_API_KEY DD_APP_KEY DD_SITE DD_SERVER_NAME DD_METRIC

demo: up load verify ## full run: cluster -> workload -> reconciliation

up: ## start the cluster and wait until healthy (+ Datadog agent if DD_API_KEY is set)
	$(COMPOSE) $(DD_PROFILE) up -d
	@bash scripts/wait-healthy.sh

load: ## build + run the worker, fire the workload
	@bash scripts/load.sh

verify: ## reconcile Path A (metric) vs Path B (histories)
	@bash scripts/verify.sh

down: ## stop and remove the cluster + volumes (incl. the Datadog agent if present)
	$(COMPOSE) --profile datadog down -v

clean: down ## also remove build artifacts and generated files
	@rm -rf bin .worker.log .sample-ids.txt .run-window
	@echo "cleaned"
