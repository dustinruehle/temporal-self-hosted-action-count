# Path A — Read the Action metric from Prometheus

**Preferred.** If your cluster is already scraped by Prometheus/Grafana, the Action
count is one query away. The Temporal Server emits an `action` counter on the frontend
that maps directly to Cloud billable Actions.

## 1. Confirm your Server version

| Version | What the metric gives you |
|---|---|
| **1.22.3+** | Closely reflects Cloud Action pricing, includes Local Activity metering |
| 1.17 – 1.22.2 | Useful for load sizing; runs low on Local Activities |
| < 1.17 | No `action` metric — use [Path B](path-b-histories.md) |

The metric is a **billing-grade estimate**, not the invoice — Temporal's docs say 1.22.3+
"more closely reflects" Cloud pricing. Use it to size and forecast, then confirm with your SA.

## 2. Total Actions over your window

```promql
sum(increase(action{service_name="frontend"}[30d]))
```

`action` is a counter, so `increase()` gives the delta across the window. For a single
Namespace, add the label:

```promql
sum(increase(action{service_name="frontend", exported_namespace="default"}[30d]))
```

> **Namespace label:** when Prometheus scrapes the Server **directly**, the label is
> `namespace`. `exported_namespace` shows up when metrics arrive via the OTel collector
> / remote-write. If one returns nothing, try the other.

## 3. Set the window end correctly

`[30d]` is evaluated at the **dashboard end time**. Set the end of your Grafana time
range to the end of the period you're measuring — the start you drag to doesn't matter,
only the end does. Leaving it at `now` while you meant last month gives the wrong answer.

> ⚠️ **`increase([30d])` needs samples spanning the whole window.** If your Server
> process is younger than the window, was restarted inside it, or Prometheus retention
> is shorter than the window, this query **silently under-reports**. Sanity-check
> against the raw counter — see [gotchas.md](gotchas.md#a1).

## 4. Capture the shape of the load

Actions per second (APS) per Namespace — the `rate()` of the counter:

```promql
sum(rate(action{service_name="frontend"}[1m])) by (exported_namespace)
```

**Mean APS** is the average of that series over your window; feed it into the monthly
formula below. **Peak APS** is its highest point — in Grafana, just read the top of the
graph over your range. In PromQL, wrap the rate in `max_over_time` as a subquery:

```promql
max_over_time( sum(rate(action{service_name="frontend"}[1m]))[24h:1m] )
```

Peak APS is what sizes your Namespace APS limits, and it's where elastic scaling pays off
versus overprovisioning self-hosted for the spike.

> A subquery like `[30d:1m]` is 43k evaluation steps and can trip Prometheus's
> `maxSamples` limit or run slowly. For long ranges, read the peak off the Grafana graph,
> or widen the resolution step (e.g. `[30d:10m]`).

## 5. Convert to a monthly figure

```
Monthly Actions = mean APS × 60 × 60 × 24 × 30   (× 2,592,000)
Example: 95 APS × 2,592,000 ≈ 246M Actions / month
```

Share the monthly total **and** your peak APS with your Temporal SA.

---
Validated end-to-end in [`harness/`](../harness) — the metric total reconciles exactly
with [Path B](path-b-histories.md).
