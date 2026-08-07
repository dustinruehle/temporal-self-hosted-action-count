# Accuracy notes

Three edge cases that can skew an Action estimate — each minor, each with a clear fix.
All three surfaced while validating both paths against a known workload in
[`../harness`](../harness) (where the self-hosted `action` metric read 400).

<a name="a1"></a>
## A1 · `increase([30d])` under-reports on "young" series

**Symptom:** the metric obviously has data, but
`sum(increase(action{service_name="frontend"}[30d]))` returns a number far too low
(in the harness: ~26 instead of 400).

**Why:** `increase()`/`rate()` measure the *rising edge inside the window*. If the
`action` series don't have samples spanning the full window, there's little edge to
measure. This happens whenever:
- the Server process is **younger** than the window,
- the Server **restarted** inside the window, or
- **Prometheus retention** is shorter than the window.

**Fix:** confirm the counter has continuous samples across the whole window. Sanity-check
against the raw counter delta between two real timestamps, e.g.:

```promql
sum(max_over_time(action{service_name="frontend"}[30d]))
  - sum(min_over_time(action{service_name="frontend"}[30d]))
```

On a fresh/short-lived cluster (like the harness) the only ground truth is the current
counter value itself — `increase()` needs history to work.

<a name="b1"></a>
## B1 · `uv add temporal-history-action-count` fails

The counter tool is **not published to PyPI**, so `uv add temporal-history-action-count`
errors with "not found in the package registry." Install from source instead:

```bash
uvx --from git+https://github.com/temporal-community/temporal-history-action-count \
  temporal-billable history.json
```

<a name="b2"></a>
## B2 · Path B double-counts child-workflow starts

A child Workflow costs **2 Actions total** — Temporal's
[metering blog](https://temporal.io/blog/upcoming-changes-to-temporal-cloud-metering)
puts it plainly: "the parent workflow spawning a child workflow [is] 1 action and the
execution of the child workflow [is] 1 action." Both are accounted **on the parent
side**, at the `StartChildWorkflowExecution` command — the child's *own*
`WorkflowExecutionStarted` event is **not** a separate Action.

The self-hosted `action` metric confirms this exactly. In the harness (25 children):

```
grpc_StartWorkflowExecution                75   # 50 transfers + 25 PARENTS — children absent
command_StartChildWorkflowExecution        25   # the child, counted...
command_StartChildWorkflowExecution_Extra  25   # ...at 2x, on the parent side
```

There is **no** `grpc_StartWorkflowExecution` for the 25 children.

**The trap:** Path B says "sample each distinct Workflow Type." The counter tool scores a
child's own history `WorkflowExecutionStarted` as 1 Action (it can't tell it's a child).
So summing a full parent history (child already at 2×) **and** a full child history
(its start again) charges the child start twice — **+1 Action per child** over what the
metric bills. (The tool's README has no warning about this.)

**Fix:** for a Workflow Type that only ever runs as a child, count its activities,
timers, etc. but **exclude its `WorkflowExecutionStarted`** — the parent's 2× already
covers it.

> In the harness this +25 over-count coincidentally cancels the 25 omitted Queries
> (Queries are billable but never in history), so the naive Path B total still reads 400.
> On a real workload the two won't cancel, so **do both**: drop child starts, add Queries.
