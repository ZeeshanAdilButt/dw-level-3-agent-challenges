"use strict";
Dashboard.register({
  id: "must-pass",
  title: "Must-pass failures",
  lab: "Lab 5",
  async render(ctx, el) {
    const L = ctx.lib;
    Dashboard.notBuilt(el, "Lab 5, part 6 (every must-pass case in every run, failures listed by id)");
  },
});
