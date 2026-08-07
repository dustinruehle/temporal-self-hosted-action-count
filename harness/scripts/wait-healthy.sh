#!/usr/bin/env bash
# Block until the Temporal frontend reports healthy.
set -euo pipefail
echo "waiting for Temporal frontend..."
for i in $(seq 1 60); do
  if docker exec temporal tctl --address temporal:7233 cluster health >/dev/null 2>&1; then
    echo "cluster healthy (after ~${i}s)"
    exit 0
  fi
  sleep 2
done
echo "cluster did not become healthy in time" >&2
exit 1
