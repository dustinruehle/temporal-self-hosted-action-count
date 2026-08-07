#!/usr/bin/env bash
# Build the worker + starter, run the worker, fire the workload, save sample IDs.
set -euo pipefail
cd "$(dirname "$0")/.."

TRANSFERS=${TRANSFERS:-50}
ORDERS=${ORDERS:-25}
SPREAD=${SPREAD:-60}   # seconds to spread starts over, so rate()/APS is measurable

mkdir -p bin
go build -o bin/worker ./worker
go build -o bin/starter ./starter

./bin/worker > .worker.log 2>&1 &
WPID=$!
trap 'kill "$WPID" 2>/dev/null || true' EXIT
echo "worker started (pid $WPID)"
sleep 4

# Record the run window (epoch seconds) so verify can read APS over exactly this span.
RUN_START=$(date +%s)
./bin/starter -transfers "$TRANSFERS" -orders "$ORDERS" -spread "$SPREAD" | tee .sample-ids.txt
RUN_END=$(date +%s)
echo "$RUN_START $RUN_END" > .run-window
echo "workload complete: $TRANSFERS transfers, $ORDERS orders (+$ORDERS children, +$ORDERS queries) over ~${SPREAD}s"
