#!/usr/bin/env bash
# Build the worker + starter, run the worker, fire the workload, save sample IDs.
set -euo pipefail
cd "$(dirname "$0")/.."

TRANSFERS=${TRANSFERS:-50}
ORDERS=${ORDERS:-25}

mkdir -p bin
go build -o bin/worker ./worker
go build -o bin/starter ./starter

./bin/worker > .worker.log 2>&1 &
WPID=$!
trap 'kill "$WPID" 2>/dev/null || true' EXIT
echo "worker started (pid $WPID)"
sleep 4

./bin/starter -transfers "$TRANSFERS" -orders "$ORDERS" | tee .sample-ids.txt
echo "workload complete: $TRANSFERS transfers, $ORDERS orders (+$ORDERS children, +$ORDERS queries)"
