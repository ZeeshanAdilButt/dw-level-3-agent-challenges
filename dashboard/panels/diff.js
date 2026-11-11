"use strict";
Dashboard.register({
  id: "diff",
  title: "Per-change diff and verdict",
  lab: "Lab 1",
  render(ctx, el) {
    const L = ctx.lib;
    Dashboard.notBuilt(el, "Lab 1, part 4 (cases fixed and broken against the named baseline, with the verdict)");
  },
});
