# Accuracy notes

Three edge cases that can skew an Action estimate — each minor, each with a clear fix.
All three surfaced while validating both paths against a known workload in
[`../harness`](../harness) (where the true answer was 400).

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

Path B says "sample each distinct Workflow Type." But a child type counted in full
includes its own `WorkflowExecutionStarted` (+1), while the **parent** history already
bills that child at **2×** via `ChildWorkflowExecutionStarted`. The billing-accurate
server metric bills a child as exactly **2 (parent 2×) + its activities** and emits no
separate start Action for it.

**Effect:** naively summing full per-type counts over-charges **+1 Action per child
execution**.

**Fix:** for a Workflow Type that only ever runs as a child, count its activities,
timers, etc. but **exclude its `WorkflowExecutionStarted`**.

> In the harness this over-count (+25) happened to cancel the omitted Queries (−25), so
> the naive total still read 400 — by coincidence. On a real workload the two won't
> cancel, so both corrections matter.
