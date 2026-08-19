# Path A — Read the Action metric from Prometheus or Datadog

**Preferred.** If your cluster is already scraped by Prometheus/Grafana **or Datadog**, the
Action count is one query away. The Temporal Server emits an `action` counter on the
frontend that maps directly to [Cloud billable Actions](https://docs.temporal.io/cloud/actions)
— Prometheus exposes it as `action`, Datadog as `io.temporal.server.action.count`. Every
query below is given in both dialects.

## 1. Confirm your Server version

| Version | What the metric gives you |
|---|---|
| **1.22.3+** | Closely reflects Cloud Action pricing, includes Local Activity metering |
| 1.17 – 1.22.2 | Useful for load sizing; runs low on Local Activities |
| < 1.17 | No `action` metric — use [Path B](path-b-histories.md) |

The metric is a **billing-grade estimate**, not the invoice — Temporal's
[migration docs](https://docs.temporal.io/cloud/migrate/estimate-actions) say versions
"1.22.3 and later provide an `action` metric that more closely reflects current Temporal
Cloud Action pricing, including Local Activity metering." Use it to size and forecast,
then confirm with your SA.

## 2. Total Actions over your window

**Prometheus / Grafana**
```promql
sum(increase(action{service_name="frontend"}[30d]))
```

**Datadog**
```
sum:io.temporal.server.action.count{$server-name}.as_count()
```

`action` is a counter. In PromQL `increase()` gives the delta across the window; in Datadog
`.as_count()` sums the counter over the dashboard time range, so set that range to your
window rather than putting it in the query. For a single Namespace, add the label:

**Prometheus / Grafana**
```promql
sum(increase(action{service_name="frontend", exported_namespace="default"}[30d]))
```

**Datadog**
```
sum:io.temporal.server.action.count{$server-name} by {namespace}.as_count()
```

> **Namespace label:** when Prometheus scrapes the Server **directly**, the label is
> `namespace`; `exported_namespace` shows up when metrics arrive via the OTel collector
> / remote-write. If one returns nothing, try the other. In Datadog the tag is `namespace`.
> `$server-name` is a template variable for your cluster tag (e.g. `kube_cluster_name:prod`)
> so the widgets aren't hard-coded to one cluster.

## 3. Set the window end correctly

`[30d]` is evaluated at the **dashboard end time**. Set the end of your Grafana time
range to the end of the period you're measuring — the start you drag to doesn't matter,
only the end does. Leaving it at `now` while you meant last month gives the wrong answer.

> ⚠️ **`increase([30d])` needs samples spanning the whole window.** If your Server
> process is younger than the window, was restarted inside it, or Prometheus retention
> is shorter than the window, this query **silently under-reports**. Sanity-check
> against the raw counter — see [gotchas.md](gotchas.md#a1).

## 4. Capture the shape of the load

Actions per second (APS) per Namespace — the rate of the counter:

**Prometheus / Grafana**
```promql
sum(rate(action{service_name="frontend"}[1m])) by (exported_namespace)
```

**Datadog**
```
sum:io.temporal.server.action.count{$server-name} by {namespace}.as_rate()
```

**Mean APS** is the average of that series over your window; feed it into the monthly
formula below. In Datadog, put the `.as_rate()` query in a query-value widget with the
**avg** aggregator. **Peak APS** is its highest point — in Grafana or Datadog, just read
the top of the graph over your range. To compute it, wrap the rate in `max_over_time`
(PromQL) or switch the widget aggregator to **max** (Datadog):

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
