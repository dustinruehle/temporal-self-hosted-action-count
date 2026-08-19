# Counting Actions on a Self-Hosted Temporal Cluster

> Measure your billable Temporal **Actions** before migrating to Cloud — the number is
> already in your environment; this shows you how to read it.

Temporal Cloud bills on Actions. A self-hosted Service doesn't surface a total the way
Cloud does, but the data is there. There are two ways to get it — **start with Path A if
you scrape metrics, otherwise Path B.** Each path below is the quick version; follow the
link for full steps and caveats.

## Path A — read the metric  ·  *preferred, if you scrape Prometheus / Grafana or Datadog*

Your Action count for the last 30 days is one query — pick your metrics backend:

**Prometheus / Grafana**
```promql
sum(increase(action{service_name="frontend"}[30d]))
```

**Datadog**
```
sum:io.temporal.server.action.count{$server-name}.as_count()
```
> Set the dashboard time range to your 30-day window (Datadog scopes `.as_count()` to the
> view). `$server-name` is a template variable for your cluster tag, e.g.
> `kube_cluster_name:prod`.

On Server **1.22.3+** this closely reflects Cloud Action pricing (incl. Local Activity
metering); it's a billing-grade **estimate**, not the invoice. (No `action` metric before
1.17 → use Path B.)

→ **[Full steps: APS + peak, per-namespace, window & label caveats](docs/path-a-metrics.md)**

## Path B — count from histories  ·  *no metrics pipeline*

Export one Event History per Workflow Type and count it:

```bash
temporal workflow show --workflow-id <id> --output json > history.json
uvx --from git+https://github.com/temporal-community/temporal-history-action-count temporal-billable history.json
```

Multiply each type's count by its monthly volume, sum, then add Queries and Heartbeats
(they're billable but never land in history).

→ **[Full steps: sampling, scaling, what history hides](docs/path-b-histories.md)**

## Turn it into a monthly figure

Path B already lands on a monthly number (per-run counts × monthly volume), and Path A's
total already **is** one. You only need the formula below if you measured Actions per
second instead (the APS query in Path A — `rate()` in PromQL, `.as_rate()` in Datadog):

```
Monthly Actions = mean APS × 2,592,000     (60 × 60 × 24 × 30)
```

Your **peak APS** comes from that same APS query — the highest point over your window.
Read it off the graph, or compute it: `max_over_time(...)` in PromQL, the `max` aggregator
on `.as_rate()` in Datadog (see [Path A](docs/path-a-metrics.md)). It's what sizes your
Namespace APS limits. The monthly total plus peak APS are the starting point for a sizing
conversation with your Temporal SA, not the final number.

## A few things to watch

Both methods have a couple of edge cases that can skew the count — an `increase()` window
that predates your metrics, the counter's git-only install, and how child Workflows are
counted. Each is minor and has a clear fix; the [gotchas](docs/gotchas.md) walk through
them.

## Validate it yourself  *(optional)*

Want proof before trusting the method? [`harness/`](harness/) stands up a disposable
cluster, runs a **known** workload, and shows both paths landing on the same number:

```bash
cd harness && make demo
```

## What's in this repo

| Path | What |
|---|---|
| [`docs/`](docs/) | the two methods in full, plus [gotchas](docs/gotchas.md) |
| [`recipe/`](recipe/) | a printable one-pager ([PDF](recipe/temporal-action-count-recipe.pdf)) and its source |
| [`harness/`](harness/) | disposable cluster + known workload that proves both paths agree |

## Reference

- [Estimate Actions for migration](https://docs.temporal.io/cloud/migrate/estimate-actions) · [What counts as an Action](https://docs.temporal.io/cloud/actions)
- [temporal-history-action-count](https://github.com/temporal-community/temporal-history-action-count) — the Path B counter
- [temporal-server-actions-count](https://github.com/temporal-sa/temporal-server-actions-count) — scripts the Path A metric sampling
- [datadog-self-hosted-queries](https://github.com/temporal-sa/datadog-self-hosted-queries) — importable Datadog widgets for the Path A queries above
