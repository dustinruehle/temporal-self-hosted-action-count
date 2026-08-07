# Counting Actions on a Self-Hosted Temporal Cluster

Temporal Cloud bills on **Actions**. Your self-hosted Service doesn't show you a total
the way Cloud does — but the number is already in your environment. This repo shows you
how to read it, **fastest path first**.

---

## The 30-second answer

**Do you scrape your cluster with Prometheus or Grafana?**

**✅ Yes →** you already have it. Run one query:

```promql
sum(increase(action{service_name="frontend"}[30d]))
```

That's your Action count for the last 30 days. → [Path A: read the metric](docs/path-a-metrics.md)

**❌ No →** count from exported Workflow histories instead:

```bash
temporal workflow show --workflow-id <id> --output json > history.json
uvx --from git+https://github.com/temporal-community/temporal-history-action-count temporal-billable history.json
```

Do that for one run of each Workflow Type, multiply by monthly volume, sum.
→ [Path B: count from histories](docs/path-b-histories.md)

**Then turn it into a monthly figure** and send it to your Temporal SA:

```
Monthly Actions = mean APS × 60 × 60 × 24 × 30   (× 2,592,000)
```

---

## Which path is mine?

| | Path A — metric | Path B — histories |
|---|---|---|
| **Use when** | you already scrape Prometheus/Grafana | you have no metrics pipeline |
| **Effort** | one PromQL query | export a few histories + run a tool |
| **Accuracy** | billing-accurate on Server **≥ 1.22.3** | good per-type estimate; some Actions not in history |
| **Covers** | everything, cluster-wide | per-Workflow-Type; **add Queries + Heartbeats manually** |

**Check your Server version first.** `1.22.3+` is billing-accurate (incl. Local
Activities). `1.17–1.22.2` is fine for load sizing but runs low. Earlier than `1.17`
has no `action` metric — use Path B.

---

## Before you trust the number

Three things bite people in practice — an under-reporting query on young clusters, a
wrong install command, and a child-workflow double-count. **Read
[docs/gotchas.md](docs/gotchas.md) before you quote a figure.**

---

## Prove it works first (optional)

Skeptical, or want to hand a customer something they can run? [`harness/`](harness/)
spins up a disposable self-hosted cluster, generates a **known** workload, and shows
**both paths landing on the same number**:

```bash
cd harness && make demo
```

→ [harness/README.md](harness/README.md)

---

## Reference

- [Estimate Actions for migration](https://docs.temporal.io/cloud/migrate/estimate-actions)
- [What counts as an Action](https://docs.temporal.io/cloud/actions)
- [Temporal Cloud pricing](https://docs.temporal.io/cloud/pricing)
- [Action counter tool](https://github.com/temporal-community/temporal-history-action-count)
- Original recipe: [`temporal-action-count-recipe.pdf`](temporal-action-count-recipe.pdf)
