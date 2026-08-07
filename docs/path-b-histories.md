# Path B — Count from exported Workflow histories

Use this when you **don't** have a metrics pipeline. You sample one Event History per
Workflow Type, count the billable Actions in it, and scale by how often that type runs.

## 1. Export one history per Workflow Type

A single run stands in for the type; you scale by volume later. From the CLI:

```bash
temporal workflow show --workflow-id <id> --output json > history.json
```

(Or use the **Download** button in the Web UI.) The counter accepts either the object
format or the plain array format these produce.

## 2. Run the counter

The tool is **not on PyPI** — install/run it from source. The simplest one-liner:

```bash
uvx --from git+https://github.com/temporal-community/temporal-history-action-count \
  temporal-billable history.json
```

Or clone it once and reuse:

```bash
git clone https://github.com/temporal-community/temporal-history-action-count
cd temporal-history-action-count && uv sync
uv run temporal-billable ../history.json
```

It prints the billable Actions in that run (e.g. `Total ... found: 7`). Child Workflows
and Local Activities are handled for you — billed at **2×** and collapsed to **1**
respectively.

## 3. Scale by volume, then add what history hides

Multiply each type's per-run count by monthly volume, then sum across types. **Then add
the Actions that never land in Event History:**

- ~**1 Action per Query**
- **Activity Heartbeats** that reach the server

If you Query or Heartbeat heavily, leaving these out understates the total.

> ⚠️ **Child-workflow double-count.** A child Workflow Type counted in full includes its
> own start — but the parent's history already bills that child at 2×. Counting both
> over-charges **+1 Action per child**. For a type that only ever runs as a child,
> count its activities/timers but **not** its `WorkflowExecutionStarted`. See
> [gotchas.md](gotchas.md#b2).

## Worked example

The three sample histories in [`../harness/histories/`](../harness/histories) count as:

| Type | Actions | Made of |
|---|---|---|
| `MoneyTransfer` | 3 | start + 2 activities |
| `OrderFulfillment` (parent) | 7 | start + 2 act + child (2×) + local-act (1) + timer |
| `ReserveInventory` (child) | 3 | start + 2 activities |

Try it:

```bash
uvx --from git+https://github.com/temporal-community/temporal-history-action-count \
  temporal-billable harness/histories/orderfulfillment.json
```

---
Validated end-to-end in [`harness/`](../harness) — these counts reconcile exactly with
the [Path A](path-a-metrics.md) metric.
