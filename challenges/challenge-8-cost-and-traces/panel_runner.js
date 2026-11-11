"use strict";
// Runs one dashboard panel against a fixed context, with a very small fake page, and prints what the panel drew as JSON.
//   node panel_runner.js <panel.js> <context.json>
// Output: {"tables": [{"caption", "head": [...], "rows": [[...]]}], "notes": [...]}.
// The tests in this folder use it, so a panel is checked on fixed data without a browser.
const fs = require("fs");
const path = require("path");

class Text { constructor(t) { this.text = String(t); } get textContent() { return this.text; } }
class Node {
  constructor(tag) { this.tagName = tag; this.children = []; this.attrs = {}; this.className = ""; this._value = undefined; }
  append(...kids) { for (const k of kids.flat()) if (k != null && k !== false) this.children.push(typeof k === "object" ? k : new Text(k)); }
  replaceChildren(...kids) { this.children = []; this.append(...kids); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener() {}
  set textContent(t) { this.children = [new Text(t)]; }
  get textContent() { return this.children.map((c) => c.textContent).join(""); }
  get value() {
    if (this._value !== undefined) return this._value;
    const first = this.children.find((c) => c.tagName === "option");
    return first ? first.attrs.value || "" : "";
  }
  set value(v) { this._value = v; }
}
globalThis.window = globalThis;
globalThis.document = { createElement: (t) => new Node(t), createElementNS: (ns, t) => new Node(t) };

const find = (node, tag, out = []) => {
  if (node.tagName === tag) out.push(node);
  for (const c of node.children || []) find(c, tag, out);
  return out;
};

async function main() {
  const [panelFile, ctxFile] = process.argv.slice(2);
  const root = path.resolve(__dirname, "..", "..");
  (0, eval)(fs.readFileSync(path.join(root, "dashboard", "lib.js"), "utf8"));
  const panels = [];
  globalThis.Dashboard = { register: (p) => panels.push(p), notBuilt: (el, label) => { const p = new Node("p"); p.append("Panel not built yet."); el.replaceChildren(p); } };
  (0, eval)(fs.readFileSync(panelFile, "utf8"));
  const ctx = JSON.parse(fs.readFileSync(ctxFile, "utf8"));
  ctx.lib = window.DashLib;
  const el = new Node("div");
  await panels[0].render(ctx, el);
  const tables = find(el, "table").map((t) => ({
    caption: (find(t, "caption")[0] || { textContent: "" }).textContent,
    head: find(t, "th").map((x) => x.textContent),
    rows: find(t, "tbody").flatMap((b) => find(b, "tr")).map((r) => find(r, "td").map((x) => x.textContent)),
  }));
  const notes = find(el, "p").map((p) => p.textContent);
  process.stdout.write(JSON.stringify({ tables, notes }));
}
main().catch((e) => { process.stderr.write(String(e && e.stack || e)); process.exit(1); });
