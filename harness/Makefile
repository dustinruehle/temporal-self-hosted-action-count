.PHONY: demo up load verify down clean

# Overridable workload size:  make demo TRANSFERS=100 ORDERS=40
TRANSFERS ?= 50
ORDERS    ?= 25
export TRANSFERS ORDERS

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
	@rm -rf bin .worker.log .sample-ids.txt
	@echo "cleaned"
