# Counting Actions on a Self-Hosted Temporal Cluster

> Measure your billable Temporal **Actions** before migrating to Cloud — the number is
> already in your environment; this shows you how to read it.

Temporal Cloud bills on Actions. A self-hosted Service doesn't surface a total the way
Cloud does, but the data is there. There are two ways to get it — **start with Path A if
you scrape metrics, otherwise Path B.** Each path below is the quick version; follow the
link for full steps and caveats.

## Path A — read the metric  ·  *preferred, if you scrape Prometheus / Grafana*

Your Action count for the last 30 days is one query:

```promql
sum(increase(action{service_name="frontend"}[30d]))
```

Billing-accurate on Server **1.22.3+**. (No `action` metric before 1.17 → use Path B.)

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

```
Monthly Actions = mean APS × 2,592,000     (60 × 60 × 24 × 30)
```

Share that total and your peak APS with your Temporal SA — it's the starting point for a
sizing conversation, not the final number.

## Before you trust the number

Three things bite people: `increase()` under-reporting on young clusters, a wrong install
command, and a child-workflow double-count. **[Read the gotchas](docs/gotchas.md)** before
you quote a figure.

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

- [Estimate Actions for migration](https://docs.temporal.io/cloud/migrate/estimate-actions) · [What counts as an Action](https://docs.temporal.io/cloud/actions) · [Cloud pricing](https://docs.temporal.io/cloud/pricing)
- [temporal-history-action-count](https://github.com/temporal-community/temporal-history-action-count) — the Path B counter
- [temporal-server-actions-count](https://github.com/temporal-sa/temporal-server-actions-count) — scripts the Path A metric sampling
- [datadog-self-hosted-queries](https://github.com/temporal-sa/datadog-self-hosted-queries) — ready-made queries if you use Datadog
