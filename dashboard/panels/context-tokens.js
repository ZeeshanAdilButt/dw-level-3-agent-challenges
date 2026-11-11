"use strict";
Dashboard.register({
  id: "context-tokens",
  title: "Context tokens per answer",
  lab: "Lab 4",
  render(ctx, el) {
    const L = ctx.lib;
    Dashboard.notBuilt(el, "Lab 4, part 1 (tokens of the delivered text, against the 3,000 token budget)");
  },
});
