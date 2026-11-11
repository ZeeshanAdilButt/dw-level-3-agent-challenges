"use strict";
// The chat UI. It only talks to /api/*; who you are comes from the session cookie, never from this page.

const $ = (id) => document.getElementById(id);
const state = { email: "", conversation: newId("conv"), principal: null };

function newId(prefix) {
  const bytes = new Uint8Array(8);
  crypto.getRandomValues(bytes);
  return prefix + "-" + Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

function node(tag, props, ...kids) {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})) {
    if (k === "class") n.className = v;
    else if (k === "text") n.textContent = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const kid of kids) if (kid != null) n.append(kid);
  return n;
}

async function api(path, options) {
  const res = await fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, options));
  let body = null;
  try { body = await res.json(); } catch (e) { /* not JSON */ }
  return { ok: res.ok, status: res.status, body };
}

function say(message, isError) {
  const el = $("signin-msg");
  el.textContent = message;
  el.className = "status" + (isError ? " error" : "");
}

function showSignedIn(principal) {
  state.principal = principal;
  $("signin").hidden = true;
  $("chat").hidden = false;
  $("who").hidden = false;
  $("who").textContent = principal.role + " " + principal.id + (principal.verified ? "" : " (not verified)");
  $("signout").hidden = false;
  $("new-conv").hidden = false;
  $("msg").focus();
}

function showSignedOut() {
  state.principal = null;
  $("signin").hidden = false;
  $("chat").hidden = true;
  $("who").hidden = true;
  $("signout").hidden = true;
  $("new-conv").hidden = true;
  $("email-form").hidden = false;
  $("code-form").hidden = true;
  say("", false);
}

async function loadOptions() {
  const res = await api("/api/signin/options");
  if (!res.ok) return;
  const list = $("fixture-emails");
  for (const row of res.body.fixture_emails) {
    list.append(node("option", { value: row.email, label: row.role }));
  }
}

$("email-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  state.email = $("email").value.trim();
  const res = await api("/api/signin", { method: "POST", body: JSON.stringify({ email: state.email }) });
  if (res.ok) {
    say(res.body.message, false);
    $("code-form").hidden = false;
    $("code").focus();
  } else say("Could not send a code.", true);
});

$("code-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const res = await api("/api/verify", { method: "POST",
    body: JSON.stringify({ email: state.email, code: $("code").value.trim() }) });
  if (res.ok) { $("code").value = ""; showSignedIn(res.body.principal); }
  else say((res.body && res.body.detail) || "Sign in failed.", true);
});

$("signout").addEventListener("click", async () => {
  await api("/api/signout", { method: "POST" });
  $("log").replaceChildren();
  $("pending").hidden = true;
  showSignedOut();
});

$("new-conv").addEventListener("click", () => {
  state.conversation = newId("conv");
  $("log").replaceChildren();
  $("pending").hidden = true;
  $("msg").focus();
});

function addTurn(who, text) {
  const li = node("li", { class: "turn " + who },
    node("div", { class: "who", text: who === "user" ? "You" : "Agent" }),
    node("p", { class: "text", text }));
  $("log").append(li);
  li.scrollIntoView({ block: "nearest" });
  return li;
}

async function openDocument(id) {
  const res = await api("/api/docs/" + encodeURIComponent(id));
  $("doc-title").textContent = res.ok ? res.body.title + " (" + id + ")" : id;
  $("doc-text").textContent = res.ok ? res.body.text : ((res.body && res.body.detail) || "Could not load it.");
  $("doc-dialog").showModal();
}
$("doc-close").addEventListener("click", () => $("doc-dialog").close());

function money(x) { return x == null ? "n/a" : "$" + Number(x).toFixed(5); }

function renderReply(li, reply) {
  if (reply.citations && reply.citations.length) {
    const row = node("div", { class: "cites" }, node("span", { class: "label", text: "Sources:" }));
    for (const id of reply.citations) {
      row.append(node("button", { type: "button", "aria-label": "Open document " + id, text: id,
        onclick: () => openDocument(id) }));
    }
    li.append(row);
  }
  if (reply.actions && reply.actions.length) {
    const ul = node("ul", { class: "actions-list" });
    for (const a of reply.actions) {
      const receipt = a.receipt && a.receipt.receipt_id ? " (receipt " + a.receipt.receipt_id + ")" : "";
      ul.append(node("li", { text: a.name + receipt }));
    }
    li.append(node("div", { class: "notice" }, node("strong", { text: "Action taken" }), ul));
  }
  if (reply.handoff) {
    const h = reply.handoff;
    li.append(node("div", { class: "notice", role: "note" },
      node("strong", { text: h.urgency === "urgent" ? "Handed to a person, urgent" : "Handed to a person" }),
      node("dl", {},
        node("dt", { text: "Reason" }), node("dd", { text: h.reason || "" }),
        node("dt", { text: "Note for them" }), node("dd", { text: h.note || "" }))));
  }
  const ms = reply.latency_ms == null ? "n/a" : (reply.latency_ms / 1000).toFixed(1) + " s";
  li.append(node("div", { class: "meta", text: "Latency " + ms + ", cost " + money(reply.cost_usd) }));
}

function showPending(question) {
  const box = $("pending");
  if (!question) { box.hidden = true; return; }
  box.replaceChildren(node("strong", { text: "The agent is waiting for your answer" }),
    node("span", { text: question }));
  box.hidden = false;
  $("msg").focus();
}

$("send-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const text = $("msg").value.trim();
  if (!text) return;
  $("send").disabled = true;
  addTurn("user", text);
  $("msg").value = "";
  const res = await api("/api/chat", { method: "POST", body: JSON.stringify({
    message: text, conversation_id: state.conversation, request_id: newId("req") }) });
  $("send").disabled = false;
  if (res.status === 401) { showSignedOut(); say("Your session ended. Sign in again.", true); return; }
  if (!res.ok) {
    addTurn("agent", "The agent did not answer. " + ((res.body && res.body.detail) || "Unknown error."));
    return;
  }
  const li = addTurn("agent", res.body.in_progress ? "Still working on your earlier request. Send again in a moment."
    : res.body.text);
  renderReply(li, res.body);
  showPending(res.body.pending);
});

(async function start() {
  loadOptions();
  const me = await api("/api/me");
  if (me.ok) showSignedIn(me.body.principal); else showSignedOut();
})();
