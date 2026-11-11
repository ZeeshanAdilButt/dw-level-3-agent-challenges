"use strict";
Dashboard.register({
  id: "failures",
  title: "Failures by type",
  lab: "Lab 8",
  render(ctx, el) {
    const L = ctx.lib;
    Dashboard.notBuilt(el, "Lab 8, part 1 (each failed case counted once, under its first matching type)");
  },
});
