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
# The poll interval MUST exceed the scrape interval — otherwise two reads can land
# on the same scrape sample and look "settled" while the counter is still climbing.
SCRAPE_INTERVAL=${SCRAPE_INTERVAL:-5}
SETTLE_SLEEP=$((SCRAPE_INTERVAL + 2))
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
  prev=$A; sleep "$SETTLE_SLEEP"
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

# --- APS shape over the run window ---
# Mean APS is the counter delta over the run divided by its duration — the definition of
# mean APS, and exactly what the monthly formula wants. (Averaging rate() samples would
# under-report here: over a ~60s run a [1m] rate never leaves its ramp.)
# Peak APS still comes from rate(): it's a genuine per-second spike.
APS_MEAN="n/a"; APS_PEAK="n/a"; DURATION=0
if [ -f .run-window ]; then
  read -r RUN_START RUN_END < .run-window
  DURATION=$((RUN_END - RUN_START))
  APS_PEAK=$(curl -s \
    --data-urlencode 'query=sum(rate(action{service_name="frontend",namespace="default"}[1m]))' \
    --data-urlencode "start=$((RUN_START-5))" --data-urlencode "end=$((RUN_END+5))" \
    --data-urlencode 'step=5s' "$PROM/api/v1/query_range" \
    | python3 -c "
import sys,json
r=json.load(sys.stdin)['data']['result']
vals=[float(v[1]) for s in r for v in s['values']] if r else []
print(f'{max(vals):.2f}' if vals else 'n/a')")
fi

# --- Path A via Datadog (optional, same counter) ---
# The Datadog agent (compose 'datadog' profile, started automatically when DD_API_KEY is
# set) forwards the same frontend `action` counter to Datadog as
# io.temporal.server.action.count. If DD_API_KEY + DD_APP_KEY are present we query
# Datadog's API for real and reconcile against the known total — exactly like the
# Prometheus check above. Without keys we just print the equivalent query so the Datadog
# form is always visible (Tier 1).
DD_METRIC=${DD_METRIC:-io.temporal.server.action.count}
DD_SERVER_NAME=${DD_SERVER_NAME:-harness}
DD_SITE=${DD_SITE:-datadoghq.com}
DD_QUERY="sum:${DD_METRIC}{server-name:${DD_SERVER_NAME}}.as_count()"
DD_COUNT="annotate"   # sentinel: no keys -> annotate only

if [ -n "${DD_API_KEY:-}" ] && [ -n "${DD_APP_KEY:-}" ] && [ -f .run-window ]; then
  read -r RUN_START RUN_END < .run-window
  echo "querying Datadog for ${DD_METRIC} (allowing for ingest lag)..."
  dd_query() {
    curl -s -G "https://api.${DD_SITE}/api/v1/query" \
      -H "DD-API-KEY: ${DD_API_KEY}" \
      -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
      --data-urlencode "from=$((RUN_START-30))" \
      --data-urlencode "to=$((RUN_END+120))" \
      --data-urlencode "query=${DD_QUERY}" \
      | python3 -c "
import sys,json
try:
    d=json.load(sys.stdin)
except Exception:
    print(-1); sys.exit()
series=d.get('series') or []
pts=[p[1] for s in series for p in s.get('pointlist',[]) if p[1] is not None]
print(round(sum(pts)) if pts else -1)"
  }
  DD_COUNT=-1; ddprev=-2
  for _ in $(seq 1 15); do
    DD_COUNT=$(dd_query || echo -1)
    if [ "$DD_COUNT" -gt 0 ] && [ "$DD_COUNT" -eq "$ddprev" ]; then break; fi
    ddprev=$DD_COUNT; sleep 8
  done
fi

python3 - "$A" "$MT" "$OF" "$RI" "$TRANSFERS" "$ORDERS" "$DURATION" "$APS_PEAK" "$DD_COUNT" "$DD_QUERY" <<'PY'
import sys
A, MT, OF, RI, T, O, DUR = map(int, sys.argv[1:8])
aps_peak = sys.argv[8]
dd_count = sys.argv[9]
dd_query = sys.argv[10]
scaled = MT*T + OF*O + RI*O
print(f"Path A  (server metric, raw counter) = {A}")
print(f"Path B  per-run: MoneyTransfer={MT} OrderFulfillment={OF} ReserveInventory={RI}")
print(f"Path B  scaled  ({MT}*{T} + {OF}*{O} + {RI}*{O}) = {scaled}")
ok = A == scaled
print(("MATCH ✅" if ok else "MISMATCH ❌") + f"  Path A {A} vs Path B {scaled}")
print("(child-2x + queries net out here — see ../docs/gotchas.md#b2)")
aps_mean = f"{A/DUR:.2f}" if DUR > 0 else "n/a"
print(f"APS over the run: mean={aps_mean}/s ({A} actions / {DUR}s) -> monthly = mean x 2,592,000")
print(f"                  peak={aps_peak}/s (rate[1m]; a shorter window surfaces higher bursts)")

# Datadog lane
dd_bad = False
print()
if dd_count == "annotate":
    import os
    have_api = bool(os.environ.get("DD_API_KEY"))
    have_app = bool(os.environ.get("DD_APP_KEY"))
    missing = " + ".join(k for k, present in (("DD_API_KEY", have_api), ("DD_APP_KEY", have_app)) if not present)
    print(f"Path A via Datadog (same counter): {dd_query}")
    if have_api and not have_app:
        print(f"  metrics are shipping to Datadog; set DD_APP_KEY to query it back and reconcile (expects {scaled}).")
    else:
        print(f"  set {missing} to query Datadog for real; it lands on the same {scaled}.")
else:
    ddn = int(dd_count)
    if ddn < 0:
        print(f"Path A via Datadog: no data returned yet (ingest lag?) — {dd_query}")
    else:
        ddok = ddn == scaled
        dd_bad = not ddok
        print(f"Path A via Datadog  (.as_count()) = {ddn}   [{dd_query}]")
        print(("MATCH ✅" if ddok else "MISMATCH ❌") + f"  Datadog {ddn} vs Path B {scaled}")

sys.exit(0 if (ok and not dd_bad) else 1)
PY
