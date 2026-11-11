"use strict";
// Starter table 2 (shipped): the headline numbers of the selected run next to the comparison run.
Dashboard.register({
  id: "headline",
  title: "Headline numbers",
  lab: "Shipped",
  render(ctx, el) {
    const L = ctx.lib;
    if (!ctx.run) { el.append(L.note("Select a run.")); return; }
    const spec = [
      ["answer_success", "Answer success", "pct"],
      ["cited_correctly", "Cited correctly", "pct"],
      ["recall5", "Recall at 5", "pct"],
      ["recall3", "Recall at 3", "pct"],
      ["mrr", "MRR", "num"],
      ["context_fact_recall", "Context fact recall", "pct"],
      ["context_tokens", "Context tokens per answer", "tok"],
      ["security_pass_rate", "Security pass rate (attacks)", "pct"],
      ["cost_p50", "Cost per answer, p50 (hosted-equivalent)", "usd"],
      ["cost_p95", "Cost per answer, p95", "usd"],
      ["latency_p50_ms", "Latency, p50", "ms"],
      ["latency_p95_ms", "Latency, p95", "ms"],
    ];
    const show = { pct: (v) => L.pct(v, 1), num: (v) => L.num(v, 3), tok: (v) => L.tok(v), usd: L.usd, ms: L.sec };
    const delta = {
      pct: (a, b) => ((a - b) * 100 >= 0 ? "+" : "") + ((a - b) * 100).toFixed(1) + " points",
      num: (a, b) => (a - b >= 0 ? "+" : "") + (a - b).toFixed(3),
      tok: (a, b) => (a - b >= 0 ? "+" : "") + L.int(a - b) + " tokens",
      usd: (a, b) => (a - b >= 0 ? "+" : "-") + L.usd(Math.abs(a - b)),
      ms: (a, b) => (a - b >= 0 ? "+" : "-") + L.sec(Math.abs(a - b)),
    };
    const rows = spec.map(([key, label, type]) => {
      const cur = L.metric(ctx.run, key), old = ctx.base ? L.metric(ctx.base, key) : { value: null, n: null };
      return { label, type, cur, old,
        change: L.isNum(cur.value) && L.isNum(old.value) ? delta[type](cur.value, old.value) : L.NA };
    }).filter((r) => L.isNum(r.cur.value) || L.isNum(r.old.value));
    const mp = L.metric(ctx.run, "must_pass_failures");
    el.append(L.table({
      caption: "Run " + ctx.run.id + (ctx.base ? ", compared with " + ctx.base.id : ", no comparison run chosen"),
      rows,
      empty: "This run has no numbers yet.",
      columns: [
        { label: "Metric", key: "label" },
        { label: "This run", key: "cur", num: true, fmt: (v, r) => show[r.type](v.value) },
        { label: "n", key: "cur", num: true, fmt: (v) => (v.n != null ? L.int(v.n) : L.NA) },
        { label: ctx.base ? "Run " + ctx.base.id : "Comparison", key: "old", num: true, fmt: (v, r) => show[r.type](v.value) },
        { label: "Change", key: "change", num: true },
      ],
    }));
    el.append(L.note("Must-pass failures in this run: " + (mp.value != null ? mp.value + " of " + (mp.n != null ? mp.n : 0) : "0 of 0")
      + ". A number that cannot be computed shows n/a, never 0% or 100%."));
  },
});
