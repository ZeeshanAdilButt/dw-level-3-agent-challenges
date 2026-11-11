"use strict";
Dashboard.register({
  id: "trace",
  title: "Trace view",
  lab: "Lab 8",
  render(ctx, el) {
    const L = ctx.lib;
    Dashboard.notBuilt(el, "Lab 8, part 2 (one case as spans: nesting, duration, tokens and cost, then the slowest and costliest steps)");
  },
});
