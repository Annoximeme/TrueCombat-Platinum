/* Public ban appeal page. No sign-in; the appeal code ties the appeal to one ban. */
"use strict";

const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function show(html, kind) {
  const r = $("#result");
  r.innerHTML = html;
  r.className = "appeal-result" + (kind ? " " + kind : "");
  r.hidden = false;
  r.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function date(t) { return new Date(t * 1000).toLocaleString(undefined, { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" }); }

async function call(path, body) {
  const r = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
  let data = {};
  try { data = await r.json(); } catch (e) { /* no body */ }
  if (!r.ok) throw new Error(data.error || "Something went wrong. Try again in a few minutes.");
  return data;
}

async function status() {
  const code = $("#code").value.trim();
  if (!code) { $("#code").focus(); return; }
  try {
    const s = await call("/appeal/status?code=" + encodeURIComponent(code));
    const ban = s.ban;
    const left = ban.active ? (ban.expires ? "until " + date(ban.expires) : "with no end date") : "no longer active";
    let html = `<p><b>Ban:</b> ${esc(ban.reason)} · ${esc(left)}</p>`;
    if (!s.appeal) html += "<p>No appeal has been sent for this ban yet.</p>";
    else if (s.appeal.status === "open") html += `<p><b>Appeal received</b> ${esc(date(s.appeal.created))}. A member of staff will review it. Check back here with the same code.</p>`;
    else html += `<p><b>Appeal ${s.appeal.status === "accepted" ? "accepted" : "denied"}</b> · ${esc(date(s.appeal.updated))}</p><p>${esc(s.appeal.answer || "")}</p>`;
    show(html, s.appeal && s.appeal.status === "accepted" ? "ok" : s.appeal && s.appeal.status === "denied" ? "bad" : "");
  } catch (e) { show(esc(e.message), "bad"); }
}

$("#check").onclick = status;
$("#appeal-form").onsubmit = async (e) => {
  e.preventDefault();
  const f = e.target;
  const btn = f.querySelector("button[type=submit]");
  btn.disabled = true;
  try {
    await call("/appeal/submit", { code: f.code.value.trim(), text: f.text.value, contact: f.contact.value });
    f.text.value = "";
    show("<p><b>Appeal sent.</b> A member of staff will review it, usually within a few days. Check the status here with the same code.</p>", "ok");
  } catch (err) { show(esc(err.message), "bad"); }
  btn.disabled = false;
};
