.PHONY: demo up load verify down clean

# Overridable workload:  make demo TRANSFERS=100 ORDERS=40 SPREAD=90
# SPREAD = seconds to pace the starts over, so rate()/APS is measurable (0 = burst).
TRANSFERS ?= 50
ORDERS    ?= 25
SPREAD    ?= 60
export TRANSFERS ORDERS SPREAD

COMPOSE = docker compose -f cluster/docker-compose.yml

demo: up load verify ## full run: cluster -> workload -> reconciliation

up: ## start the cluster and wait until healthy
	$(COMPOSE) up -d
	@bash scripts/wait-healthy.sh

load: ## build + run the worker, fire the workload
	@bash scripts/load.sh

verify: ## reconcile Path A (metric) vs Path B (histories)
	@bash scripts/verify.sh

down: ## stop and remove the cluster + volumes
	$(COMPOSE) down -v

clean: down ## also remove build artifacts and generated files
	@rm -rf bin .worker.log .sample-ids.txt .run-window
	@echo "cleaned"
