"use strict";
// Renders one dashboard panel in plain Node with a tiny fake DOM, so a test can read what the panel draws.
//   node panel_render.js <dashboard folder> <panel file name> <context json file>
// Prints one JSON object: {"text": "...", "tables": [[["cell", ...], ...]], "notBuilt": true or false}.
// No browser is needed. The context file holds run, base, cases, baseCases, runs and kept, as the shell passes them.
const fs = require("fs");
const path = require("path");
const vm = require("vm");

class TextNode {
  constructor(text) { this.nodeType = 3; this.data = String(text); }
}

class Elem {
  constructor(tag) {
    this.nodeType = 1; this.tag = tag; this.children = []; this.attrs = {}; this.className = ""; this.listeners = {};
  }
  set textContent(v) { this.children = [new TextNode(v)]; }
  get textContent() { return this.children.map((c) => (c.nodeType === 3 ? c.data : c.textContent)).join(""); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener(name, fn) { this.listeners[name] = fn; }
  append(...kids) {
    for (const k of kids) {
      if (k == null) continue;
      this.children.push(k && k.nodeType ? k : new TextNode(k));
    }
  }
  replaceChildren(...kids) { this.children = []; this.append(...kids); }
}

function walk(node, fn) {
  fn(node);
  if (node.children) for (const c of node.children) walk(c, fn);
}

function tablesOf(root) {
  const out = [];
  walk(root, (n) => {
    if (n.tag !== "table") return;
    const rows = [];
    walk(n, (r) => {
      if (r.tag !== "tr") return;
      rows.push(r.children.filter((c) => c.tag === "td" || c.tag === "th").map((c) => c.textContent.trim()));
    });
    out.push(rows);
  });
  return out;
}

const [dashDir, panelName, ctxFile] = process.argv.slice(2);
global.window = global;
global.document = { createElement: (t) => new Elem(t), createElementNS: (ns, t) => new Elem(t) };
for (const f of ["lib.js", "dashboard.js"]) vm.runInThisContext(fs.readFileSync(path.join(dashDir, f), "utf8"), { filename: f });

let panel = null;
const realRegister = global.Dashboard.register;
global.Dashboard.register = (p) => { panel = p; };
vm.runInThisContext(fs.readFileSync(path.join(dashDir, "panels", panelName), "utf8"), { filename: panelName });
global.Dashboard.register = realRegister;

const ctx = JSON.parse(fs.readFileSync(ctxFile, "utf8"));
ctx.lib = global.DashLib;
ctx.runs = ctx.runs || [];
ctx.cases = ctx.cases || [];
ctx.baseCases = ctx.baseCases || [];
ctx.select = () => {};
const el = new Elem("div");
Promise.resolve(panel.render(ctx, el)).then(() => {
  const text = el.textContent;
  process.stdout.write(JSON.stringify({ text, tables: tablesOf(el), notBuilt: /Panel not built yet/.test(text) }));
});
