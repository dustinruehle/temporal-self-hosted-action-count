#!/usr/bin/env bash
# Reconcile Path A (server metric) against Path B (history counter) for the workload.
set -euo pipefail
cd "$(dirname "$0")/.."

TRANSFERS=${TRANSFERS:-50}
ORDERS=${ORDERS:-25}
PROM=${PROM:-http://localhost:9090}
export TEMPORAL_ADDRESS=${TEMPORAL_ADDRESS:-localhost:7233}
COUNTER="git+https://github.com/temporal-community/temporal-history-action-count"

if [ ! -f .sample-ids.txt ]; then
  echo "no .sample-ids.txt — run 'make load' first" >&2; exit 1
fi

# --- Path A: authoritative server metric (raw counter, default namespace) ---
# Prometheus scrapes every 5s; the workload finishes in seconds. Poll until the
# counter stops rising (two equal, non-zero reads) so we don't read mid-scrape.
read_counter() {
  curl -s --data-urlencode \
    'query=sum(action{service_name="frontend",namespace="default"})' \
    "$PROM/api/v1/query" \
    | python3 -c "import sys,json;r=json.load(sys.stdin)['data']['result'];print(int(float(r[0]['value'][1])) if r else 0)"
}
echo "waiting for the action counter to settle..."
A=0; prev=-1
for _ in $(seq 1 20); do
  A=$(read_counter)
  if [ "$A" -gt 0 ] && [ "$A" -eq "$prev" ]; then break; fi
  prev=$A; sleep 3
done

# --- Path B: export one history per Workflow Type, count each ---
mkdir -p histories
mt=$(grep '^MoneyTransfer='    .sample-ids.txt | cut -d= -f2)
of=$(grep '^OrderFulfillment=' .sample-ids.txt | cut -d= -f2)
ri=$(grep '^ReserveInventory=' .sample-ids.txt | cut -d= -f2)
temporal workflow show --workflow-id "$mt" --output json > histories/moneytransfer.json
temporal workflow show --workflow-id "$of" --output json > histories/orderfulfillment.json
temporal workflow show --workflow-id "$ri" --output json > histories/reserveinventory.json

count() { uvx --from "$COUNTER" temporal-billable "$1" 2>/dev/null \
            | grep -oE 'found: [0-9]+' | grep -oE '[0-9]+'; }
MT=$(count histories/moneytransfer.json)
OF=$(count histories/orderfulfillment.json)
RI=$(count histories/reserveinventory.json)

# --- APS shape: mean + peak of rate() over the run window (like reading a Grafana graph) ---
# rate()/APS is only meaningful over sustained load, so we read it across the whole
# paced run rather than at a single instant (which would show ~0 once the run ends).
APS_MEAN="n/a"; APS_PEAK="n/a"
if [ -f .run-window ]; then
  read -r RUN_START RUN_END < .run-window
  APS_JSON=$(curl -s \
    --data-urlencode 'query=sum(rate(action{service_name="frontend",namespace="default"}[1m]))' \
    --data-urlencode "start=$((RUN_START-5))" --data-urlencode "end=$((RUN_END+5))" \
    --data-urlencode 'step=5s' "$PROM/api/v1/query_range")
  read -r APS_MEAN APS_PEAK <<EOF
$(printf '%s' "$APS_JSON" | python3 -c "
import sys,json
r=json.load(sys.stdin)['data']['result']
vals=[float(v[1]) for s in r for v in s['values']] if r else []
print(f'{sum(vals)/len(vals):.2f} {max(vals):.2f}' if vals else 'n/a n/a')")
EOF
fi

python3 - "$A" "$MT" "$OF" "$RI" "$TRANSFERS" "$ORDERS" "$APS_MEAN" "$APS_PEAK" <<'PY'
import sys
A, MT, OF, RI, T, O = map(int, sys.argv[1:7])
aps_mean, aps_peak = sys.argv[7], sys.argv[8]
scaled = MT*T + OF*O + RI*O
print(f"Path A  (server metric, raw counter) = {A}")
print(f"Path B  per-run: MoneyTransfer={MT} OrderFulfillment={OF} ReserveInventory={RI}")
print(f"Path B  scaled  ({MT}*{T} + {OF}*{O} + {RI}*{O}) = {scaled}")
ok = A == scaled
print(("MATCH ✅" if ok else "MISMATCH ❌") + f"  Path A {A} vs Path B {scaled}")
print("(child-2x + queries net out here — see ../docs/gotchas.md#b2)")
print(f"APS over the run: mean={aps_mean}/s  peak={aps_peak}/s  (feeds the monthly = mean APS x 2,592,000 projection)")
sys.exit(0 if ok else 1)
PY
