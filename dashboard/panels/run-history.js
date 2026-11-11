"use strict";
// Starter table 1 (shipped): every run, newest first. Click a row to select that run.
Dashboard.register({
  id: "run-history",
  title: "Run history",
  lab: "Shipped",
  render(ctx, el) {
    const L = ctx.lib;
    const rows = [...ctx.runs].reverse().map((r) => ({
      id: r.id,
      parent: r.parent,
      change: L.changeText(r),
      path: L.modelPathOf(r),
      answer: L.metric(r, "answer_success"),
      recall5: L.metric(r, "recall5"),
      cost: L.metric(r, "cost_p50"),
      latency: L.metric(r, "latency_p50_ms"),
      kept: r.id === ctx.kept,
    }));
    el.append(L.table({
      caption: "All runs, newest first (click a row to select it)",
      rows,
      rowKey: (r) => r.id,
      selected: ctx.run && ctx.run.id,
      onRowClick: (r) => ctx.select(r.id),
      empty: "No runs yet.",
      columns: [
        { label: "Run", key: "id", fmt: (v, r) => v + (r.kept ? " (kept)" : "") },
        { label: "Parent", key: "parent", fmt: (v) => v || "none" },
        { label: "Change", key: "change" },
        { label: "Model path", key: "path" },
        { label: "Answer success", key: "answer", num: true, fmt: (v) => L.pct(v.value) + (v.n != null ? " of " + v.n : "") },
        { label: "Recall at 5", key: "recall5", num: true, fmt: (v) => L.pct(v.value) },
        { label: "Cost p50 per answer", key: "cost", num: true, fmt: (v) => L.usd(v.value) },
        { label: "Latency p50", key: "latency", num: true, fmt: (v) => L.sec(v.value) },
      ],
    }));
  },
});
