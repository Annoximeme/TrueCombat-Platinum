/* Staff portal front end. Plain JavaScript, no build step. Every value from the servers is escaped before it is shown. */
"use strict";

const S = { me: null, servers: [], timers: [], subs: [], live: false, chatAfter: 0, page: "", templates: null, events: {} };
const $ = (sel, root = document) => root.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const can = (perm) => !!(S.me && S.me.perms.includes(perm));
const TEAM = { 0: "None", 1: "Terrorists", 2: "Specops" };

function ago(t) {
  if (!t) return "never";
  const s = Math.max(0, Math.floor(Date.now() / 1000 - t));
  if (s < 60) return s + "s ago";
  if (s < 3600) return Math.floor(s / 60) + "m ago";
  if (s < 86400) return Math.floor(s / 3600) + "h ago";
  return Math.floor(s / 86400) + "d ago";
}
function when(t) {
  if (!t) return "";
  return new Date(t * 1000).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
}
function clock(t) { return new Date(t * 1000).toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }); }
function until(t) {
  if (!t) return "permanent";
  const s = t - Date.now() / 1000;
  if (s <= 0) return "expired";
  if (s < 3600) return Math.ceil(s / 60) + " min left";
  if (s < 86400 * 2) return Math.round(s / 3600) + " h left";
  return Math.round(s / 86400) + " days left";
}
function dur(s) {
  if (!s) return "";
  if (s < 60) return s + "s";
  if (s < 3600) return Math.floor(s / 60) + "m";
  return Math.floor(s / 3600) + "h " + Math.floor((s % 3600) / 60) + "m";
}

async function api(path, body) {
  const opt = { headers: {}, credentials: "same-origin" };
  if (body !== undefined) {
    opt.method = "POST";
    opt.headers["Content-Type"] = "application/json";
    opt.headers["X-CSRF"] = S.me ? S.me.csrf : "";
    opt.body = JSON.stringify(body);
  }
  const r = await fetch("/api/" + path, opt);
  let data = {};
  try { data = await r.json(); } catch (e) { /* empty answer */ }
  if (r.status === 401 && S.me) { location.reload(); }
  if (!r.ok) throw new Error(data.error || "The portal did not answer (" + r.status + ").");
  return data;
}

function toast(msg, bad, undoId) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (bad ? " bad" : "");
  if (undoId) {
    const b = document.createElement("button");
    b.className = "btn btn-small";
    b.textContent = "Undo";
    b.onclick = async () => {
      b.disabled = true;
      try { const r = await api("undo", { id: undoId }); toast(r.message); if (S.page.startsWith("server/")) drawServer(S.page.slice(7)); } catch (e) { toast(e.message, true); }
    };
    t.appendChild(b);
  }
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, undoId ? 15000 : bad ? 7000 : 3500);
}
function md(text) { return esc(text).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>"); }
function susTag(score) {
  if (score == null || score < 25) return "";
  return `<span class="sus ${score >= 60 ? "high" : "mid"}" title="Suspicion score">${score}</span>`;
}

/* saved replies: a select that fills a field of the dialog */
async function templates() {
  if (!S.templates) S.templates = (await api("templates").catch(() => ({ templates: [] }))).templates;
  return S.templates;
}
function tplSelect(kind, field) {
  const list = (S.templates || []).filter((t) => t.kind === kind);
  if (!list.length) return "";
  return `<label>Saved reply</label><select data-tpl="${esc(field)}"><option value="">Write your own</option>${list.map((t) => `<option value="${esc(t.text)}">${esc(t.title)}</option>`).join("")}</select>`;
}

/* ------------------------------------------------------------------ modal */
function modal({ title, sub = "", body = "", ok = "Confirm", danger = false, onOk }) {
  const m = $("#modal");
  $("#modal-title").textContent = title;
  $("#modal-sub").textContent = sub;
  $("#modal-sub").hidden = !sub;
  $("#modal-body").innerHTML = body;
  $("#modal-error").hidden = true;
  const okBtn = $("#modal-ok");
  okBtn.textContent = ok;
  okBtn.className = "btn " + (danger ? "btn-primary" : "btn-primary");
  okBtn.disabled = false;
  okBtn.hidden = false;
  $("#modal-body").onclick = null;
  m.hidden = false;
  for (const sel of $("#modal-body").querySelectorAll("select[data-tpl]")) {
    sel.onchange = () => { const f = $("#modal-body").querySelector(`[name="${sel.dataset.tpl}"]`); if (f && sel.value) f.value = sel.value; };
  }
  const first = $("#modal-body input, #modal-body select, #modal-body textarea");
  (first || okBtn).focus();
  $("#modal-form").onsubmit = async (e) => {
    e.preventDefault();
    okBtn.disabled = true;
    try {
      const form = {};
      for (const el of $("#modal-body").querySelectorAll("[name]")) form[el.name] = el.type === "checkbox" ? el.checked : el.value;
      await onOk(form);
      m.hidden = true;
    } catch (err) {
      $("#modal-error").textContent = err.message;
      $("#modal-error").hidden = false;
      okBtn.disabled = false;
    }
  };
}
function closeModal() { $("#modal").hidden = true; }

/* ------------------------------------------------------------------ boot */
async function boot() {
  const params = new URLSearchParams(location.search);
  const msg = { failed: "Sign-in did not complete. Try again.", denied: "This Discord account has no staff role. Ask an admin to add you.",
    discord: "Discord did not answer. Try again in a minute.", slow: "Too many sign-in attempts. Wait a few minutes." }[params.get("signin")];
  if (msg) history.replaceState(null, "", "/" + location.hash);
  const me = await api("me").catch(() => ({ signed_in: false }));
  if (!me.signed_in) {
    $("#signin").hidden = false;
    if (msg) { $("#signin-msg").textContent = msg; $("#signin-msg").hidden = false; }
    $("#dev-login").hidden = !me.dev_login;
    return;
  }
  S.me = me;
  if (me.mfa_pending) return mfaScreen();
  $("#app").hidden = false;
  $("#me-name").textContent = me.name;
  $("#me-role").textContent = me.role;
  if (me.avatar) { $("#me-avatar").src = me.avatar; $("#me-avatar").hidden = false; }
  for (const a of document.querySelectorAll("#nav a[data-perm]")) a.hidden = !can(a.dataset.perm);
  for (const g of document.querySelectorAll("#nav .nav-group")) g.hidden = ![...g.querySelectorAll("a")].some((a) => !a.hidden);
  navSetup();
  paletteSetup();
  $("#logout").onclick = async () => { await api("../auth/logout", {}).catch(() => {}); location.href = "/"; };
  $("#me-account").onclick = accountDialog;
  templates();
  $("#modal-cancel").onclick = closeModal;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") { closeModal(); closePalette(); closeNav(); } });
  document.addEventListener("keydown", shortcutKey);
  window.addEventListener("hashchange", route);
  every(refreshReportCount, 30000);
  every(refreshAlertCount, 30000);
  every(refreshCaseCount, 60000);
  every(refreshAcCount, 60000);
  every(refreshCommentCount, 60000);
  every(refreshDuty, 60000);
  liveSetup();
  if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
  route();
}

function mfaScreen() {
  $("#mfa").hidden = false;
  const f = $("#mfa-form");
  f.code.focus();
  f.onsubmit = async (e) => {
    e.preventDefault();
    try { await api("2fa/verify", { code: f.code.value }); location.reload(); } catch (err) { $("#mfa-msg").textContent = err.message; $("#mfa-msg").hidden = false; f.code.select(); }
  };
}

async function refreshAlertCount() {
  try {
    const r = await api("alerts");
    const seen = +(localStorage.getItem("alerts-seen") || 0);
    const n = r.alerts.filter((a) => a.id > seen).length;
    $("#nav-alerts").textContent = n > 99 ? "99+" : n;
    $("#nav-alerts").hidden = !n || S.page === "alerts";
  } catch (e) { /* ignore */ }
}

const PUSH_ROW = '<p class="staffkey-row"><button type="button" class="btn btn-small" data-push>Alerts on this device</button> <span class="dim small">Phone or desktop notifications: urgent alerts always, everything while you are on duty.</span></p>';
const STAFF_KEY_ROW = '<p class="staffkey-row"><button type="button" class="btn btn-small" data-staffkey>Staff badge in game</button> <span class="dim small">Get the key file that shows you as staff on our servers.</span></p>';
function accountDialog() {
  setTimeout(() => { $("#modal-body").onclick = (e) => {
    if (e.target.closest("[data-staffkey]")) staffKeyDialog().catch((err) => toast(err.message, true));
    if (e.target.closest("[data-push]")) pushDialog().catch((err) => toast(err.message, true));
  }; }, 0);
  const me = S.me;
  const status = me.mfa_on ? '<p><span class="tag ok">On</span> Two-step sign-in protects this account.</p>'
    : `<p><span class="tag ${me.mfa_required ? "bad" : ""}">Off</span> ${me.mfa_required ? "Admin tools stay locked until you turn it on." : "Optional for moderators, and recommended."}</p>`;
  if (me.mfa_on) {
    return modal({ title: "Your account", sub: me.name + " · " + me.role, ok: me.mfa_required ? "Close" : "Turn off", danger: !me.mfa_required,
      body: status + PUSH_ROW + STAFF_KEY_ROW + (me.mfa_required ? "" : '<label>Code from your app, to turn it off</label><input name="code" inputmode="numeric" maxlength="7">'),
      onOk: async (f) => { if (me.mfa_required) return; await api("2fa/disable", { code: f.code }); toast("Two-step sign-in is off."); setTimeout(() => location.reload(), 800); } });
  }
  modal({ title: "Your account", sub: me.name + " · " + me.role, ok: "Set up two-step sign-in", body: status + '<p class="muted">You need an authenticator app such as Google Authenticator, Microsoft Authenticator, 1Password or Aegis.</p>' + PUSH_ROW + STAFF_KEY_ROW,
    onOk: async () => {
      const r = await api("2fa/setup", {});
      setTimeout(() => modal({ title: "Set up two-step sign-in", ok: "Turn on",
        sub: "Scan the code with your authenticator app, then type the code it shows.",
        body: `<div class="qr"><img src="${esc(r.qr)}" width="200" height="200" alt="QR code for your authenticator app"></div>
          <label>Can't scan? Type this key instead</label><div class="secret">${esc(r.secret.replace(/(.{4})/g, "$1 ").trim())}</div>
          <p class="small"><a href="${esc(r.uri)}">Open in an authenticator app on this device</a></p>
          <label>Code from the app</label><input name="code" inputmode="numeric" autocomplete="one-time-code" maxlength="7" required>`,
        onOk: async (f) => { await api("2fa/enable", { code: f.code }); toast("Two-step sign-in is on."); setTimeout(() => location.reload(), 800); } }), 0);
    } });
}

/* in-game staff badge: the key pair is made here in the browser; only the public half goes to the portal */
async function makeStaffKey() {
  if (!crypto.subtle || !crypto.subtle.generateKey) throw new Error("This browser cannot make keys. Use an up-to-date Chrome, Edge, Firefox or Safari.");
  let pair;
  try { pair = await crypto.subtle.generateKey({ name: "Ed25519" }, true, ["sign", "verify"]); }
  catch (e) { throw new Error("This browser cannot make Ed25519 keys yet. Update it, or use an up-to-date Chrome, Edge, Firefox or Safari."); }
  const hex = (buf) => [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
  const pub = hex(await crypto.subtle.exportKey("raw", pair.publicKey));
  const pkcs8 = new Uint8Array(await crypto.subtle.exportKey("pkcs8", pair.privateKey));
  const seed = hex(pkcs8.slice(pkcs8.length - 32));
  const r = await api("staffkey", { public: pub });
  const blob = new Blob([`TCPSTAFF1 ${r.id} ${seed}\r\n`], { type: "application/octet-stream" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = "staff.key";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  return r;
}

async function staffKeyDialog() {
  const k = await api("staffkey");
  const state = !k.key ? '<p><span class="tag">None</span> You have no staff key yet.</p>'
    : `<p><span class="tag ${k.active ? "ok" : "bad"}">${k.active ? "Active" : "Not active"}</span> Key made ${when(k.key.created)}.${k.active ? "" : " Sign in to the portal regularly to keep it active."}</p>`;
  const renew = k.key ? " A new key cancels the old one straight away." : "";
  if (!k.launcher) {   // until the launcher that installs keys is out: the key file is the way
    return modal({ title: "Staff badge in game", sub: "Your staff key shows your staff badge and orange name on our servers.", ok: k.key ? "Get a new key" : "Get my staff key",
      body: state + `<p class="muted">The key is made in this browser and downloads as <b>staff.key</b>. The portal never sees the secret part, so keep the file to yourself.${renew}</p>`,
      onOk: async () => { setTimeout(() => staffKeyDownload().catch((err) => toast(err.message, true)), 0); } });
  }
  modal({ title: "Staff badge in game", sub: "Your staff key shows your staff badge and orange name on our servers.", ok: "Install in game",
    body: state + `<p class="muted">Install in game hands the job to the TrueCombat Platinum launcher on this PC: it makes the key and puts it in your game's profile folder. The secret part never leaves your PC.${renew}</p>
      <p class="small">No launcher on this PC? <button type="button" class="linkish" data-download>Download the key file instead</button>.</p>`,
    onOk: async () => {
      const r = await api("staffkey/link", {});
      const before = k.key ? k.key.id : "";
      location.href = r.link;
      setTimeout(() => launcherWait(before), 0);
    } });
  $("#modal-body").onclick = (e) => { if (e.target.closest("[data-download]")) staffKeyDownload().catch((err) => toast(err.message, true)); };
}

function launcherWait(before) {
  modal({ title: "Installing your staff key", ok: "Close",
    body: `<p id="kw-state"><span class="tag">Waiting</span> Your launcher should open and install the key. Allow it if your browser asks to open TrueCombat Platinum.</p>
      <p class="muted small">Needs launcher 2.1 or newer. Nothing happening? Update the launcher, or use "Download the key file instead".</p>`,
    onOk: () => {} });
  const started = Date.now();
  const tick = async () => {
    if ($("#modal").hidden || Date.now() - started > 180000) return;
    const k = await api("staffkey").catch(() => null);
    if (k && k.key && k.key.id !== before) {
      const el = $("#kw-state");
      if (el) el.innerHTML = '<span class="tag ok">Installed</span> Your key is in the game. Start TrueCombat Platinum and join one of our servers.';
      return;
    }
    setTimeout(tick, 2500);
  };
  setTimeout(tick, 2500);
}

async function staffKeyDownload() {
  const r = await makeStaffKey();
  modal({ title: "Install your staff key", ok: "Done",
    body: `<ol class="steps"><li>Move the downloaded <b>staff.key</b> into the <b>profile</b> folder of your game, for example <span class="mono">C:\\Games\\TrueCombat Platinum\\profile</span>.</li>
      <li>Start the game. It locks the key to your Windows account the first time it reads it.</li>
      <li>Join one of our servers: your name shows in staff orange on the scoreboard.</li></ol>
      <p class="small">No download? <a href="${makeStaffKey.url}" download="staff.key">Save staff.key</a>. This link works only until you close the portal.</p>
      <p class="muted">Don't share the file. If it leaks or you change PC, just get a new key here.</p>${r.problems && r.problems.length ? `<p class="error">Some servers did not take the new key yet: ${esc(r.problems.join("; "))}</p>` : ""}`,
    onOk: () => {} });
}

/* fn now and every ms; with live updates on, a page that names the event kinds it shows refreshes when they happen
   and its timer only runs every fourth time, as a safety net */
function every(fn, ms, page, kinds) {
  fn();
  let tick = 0;
  const id = setInterval(() => {
    if (page && S.page !== page) return;
    if (kinds && S.live && ++tick % 4) return;
    fn();
  }, ms);
  if (page) { S.timers.push(id); if (kinds) S.subs.push({ fn, kinds, page }); }
  return id;
}

async function refreshReportCount() {
  if (!can("reports")) return;
  try {
    const r = await api("reports?status=open");
    const n = (r.counts.open || 0) + (r.counts.claimed || 0);
    $("#nav-reports").textContent = n;
    $("#nav-reports").hidden = !n;
  } catch (e) { /* ignore */ }
}

function route() {
  closeModal();                 // a dialog belongs to the page it was opened on
  S.timers.forEach(clearInterval);
  S.timers = [];
  S.subs = [];
  closeNav();
  const parts = (location.hash || "#/home").slice(2).split("/");
  const page = parts[0] || "home";
  S.page = page + (parts[1] ? "/" + parts[1] : "");
  for (const a of document.querySelectorAll("#nav a")) a.classList.toggle("on", a.dataset.page === page || (page === "server" && a.dataset.page === "servers") || (page === "player" && a.dataset.page === "players") || (page === "case" && a.dataset.page === "cases"));
  const main = $("#main");
  main.innerHTML = '<p class="empty">Loading…</p>';
  const pages = { home: pageHome, servers: pageServers, server: pageServer, chat: pageChat, reports: pageReports, players: pagePlayers,
    player: pagePlayer, bans: pageBans, audit: pageAudit, staff: pageStaff, health: pageHealth, alerts: pageAlerts,
    watchlist: pageWatchlist, review: pageReview, schedule: pageSchedule, filter: pageFilter, replies: pageReplies,
    weekly: pageWeekly, settings: pageSettings, insights: pageInsights, cases: pageCases, case: pageCase,
    history: pageHistory, quality: pageQuality, anticheat: pageAnticheat, comments: pageComments };
  let arg = "";
  try { arg = decodeURIComponent(parts[1] || ""); } catch (e) { arg = ""; }      // a broken link opens the page, not a blank screen
  (pages[page] || pageHome)(main, arg);
  if (S.me.mfa_required && !S.me.mfa_on) {
    main.insertAdjacentHTML("afterbegin", '<div class="banner"><span>Admin tools stay locked until you turn on two-step sign-in.</span><button class="btn btn-small" id="mfa-now">Set it up</button></div>');
    $("#mfa-now").onclick = accountDialog;
  }
  if (page === "alerts") $("#nav-alerts").hidden = true;
  main.focus({ preventScroll: true });
}

/* ------------------------------------------------------------------ servers */
async function loadServers() {
  const r = await api("servers");
  S.servers = r.servers;
  return r.servers;
}
function eacTag(s) {
  return s.eac === "required" ? '<span class="tag ok">EAC required</span>' : s.eac === "on" ? '<span class="tag warn">EAC on</span>' : '<span class="tag bad">EAC off</span>';
}

function pageServers(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Live</p><h1>Servers</h1></div>
    <div class="actions">${can("server.say") ? '<button class="btn" id="say-all">Message every server</button>' : ""}</div></div>
    <div class="cards" id="cards"></div>`;
  const sayAll = $("#say-all");
  if (sayAll) sayAll.onclick = () => sayDialog("*");
  every(async () => {
    try {
      const list = await loadServers();
      $("#cards").innerHTML = list.map((s) => `
        <a class="card" href="#/server/${esc(s.key)}">
          <div class="tags"><span class="tag">${esc(s.kind || "official")}</span>${s.online ? eacTag(s) : ""}
            ${s.ranked ? '<span class="tag staff">Ranked</span>' : ""}${s.needpass ? '<span class="tag">Password</span>' : ""}</div>
          <div class="title"><span class="dot ${s.online ? "on" : "off"}"></span>${esc(s.name)}</div>
          <div class="meta">${s.online ? esc(s.map) + (s.mode ? " · " + esc(s.mode) : "") : "Offline · " + esc(s.error || "no answer")}</div>
          <div class="big">${s.online ? s.humans : "–"}<small> players${s.bots ? " · " + s.bots + " bots" : ""} · ${s.max_players || "?"} slots</small></div>
        </a>`).join("") || '<p class="empty">No servers configured.</p>';
    } catch (e) { toast(e.message, true); }
  }, 5000, "servers", ["servers"]);
}

function pageServer(main, key) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow"><a href="#/servers">Servers</a></p><h1 id="srv-title">Server</h1>
      <div class="muted" id="srv-meta"></div></div><div class="actions" id="srv-actions"></div></div>
    <div id="event-banner"></div>
    <div class="grid grid-2">
      <div><div class="panel"><div class="table-wrap"><table id="players"></table></div></div>
        <div class="panel"><h3>Server control</h3><div id="controls" class="tags"></div></div>
        ${can("livemap") ? '<div class="panel"><div class="head"><h3>Live map</h3><button class="btn btn-small" id="map-toggle">Show live map</button></div><p class="dim small" id="map-note">Positions of every player, refreshed every two seconds. Opening it is recorded in the audit log, and it stays closed while you play on this server.</p><div id="livemap"></div></div>' : ""}</div>
      <div class="panel chat"><h3>Chat</h3><div class="chat-log" id="chat-log"></div>
        ${can("chat.reply") ? '<form class="chat-form" id="chat-form"><input name="text" maxlength="200" placeholder="Reply as staff" autocomplete="off"><button class="btn btn-primary">Send</button></form>' : ""}</div>
    </div>`;
  S.chatAfter = 0;
  const controls = [];
  if (can("server.say")) controls.push('<button class="btn btn-small" data-c="say">Announce</button>');
  if (can("server.map")) controls.push('<button class="btn btn-small" data-c="map">Change map now</button>', '<button class="btn btn-small" data-c="nextmap">Skip to next map</button>', '<button class="btn btn-small" data-c="rotation">Edit rotation</button>');
  if (can("server.restart")) controls.push('<button class="btn btn-small btn-danger" data-c="restart">Restart match</button>');
  if (can("server.say")) controls.push('<button class="btn btn-small" data-c="schedule">Schedule</button>');
  if (can("event")) controls.push('<button class="btn btn-small" data-c="event">Event mode</button>');
  if (can("cvars")) controls.push(`<a class="btn btn-small" href="#/settings/${esc(key)}">Settings</a>`);
  $("#controls").innerHTML = controls.join("") || '<span class="dim">Your role has no server controls.</span>';
  $("#controls").onclick = (e) => { const c = e.target.dataset.c; if (c) serverControl(key, c); };
  const form = $("#chat-form");
  if (form) form.onsubmit = async (e) => {
    e.preventDefault();
    const text = form.text.value.trim();
    if (!text) return;
    try { await api("server", { server: key, action: "chat", text }); form.text.value = ""; pollChat(key); } catch (err) { toast(err.message, true); }
  };
  $("#players").onclick = (e) => { const b = e.target.closest("button[data-a]"); if (b) playerAction(key, +b.dataset.slot, b.dataset.name, b.dataset.a, b.dataset.pid); };
  const mt = $("#map-toggle");
  if (mt) mt.onclick = () => {
    const on = mt.textContent.startsWith("Show");
    mt.textContent = on ? "Hide live map" : "Show live map";
    if (on) { S.mapTimer = every(() => drawMap(key), 2000, "server/" + key); } else { clearInterval(S.mapTimer); $("#livemap").innerHTML = ""; }
  };
  every(() => drawServer(key), 3000, "server/" + key, ["servers", "action"]);
  every(() => pollChat(key), 2000, "server/" + key, ["chat"]);
}

async function drawServer(key) {
  let s;
  try { s = (await loadServers()).find((x) => x.key === key); } catch (e) { toast(e.message, true); return; }
  if (!s) { $("#main").innerHTML = '<p class="empty">Unknown server.</p>'; return; }
  $("#srv-title").innerHTML = `<span class="dot ${s.online ? "on" : "off"}"></span>${esc(s.name)}`;
  $("#srv-meta").innerHTML = s.online
    ? `${esc(s.map)}${s.mode ? " · " + esc(s.mode) : ""} · ${s.humans} players${s.bots ? ", " + s.bots + " bots" : ""} of ${s.max_players} · ${eacTag(s)} <span class="mono dim">${esc(s.address)}</span>`
    : `<span class="error">Offline: ${esc(s.error || "no answer")}</span>`;
  const extra = s.staff_commands && s.staff_commands.length;
  const rows = (s.players || []).slice().sort((a, b) => (a.team || 9) - (b.team || 9) || b.score - a.score);
  const kd = extra || rows.some((p) => p.kills != null);
  const head = `<tr><th>Player</th><th>Team</th><th class="num">Score</th>${kd ? '<th class="num">K/D</th>' : ""}<th class="num">Ping</th><th>Anti-cheat</th><th class="num">Time</th><th></th></tr>`;
  const body = rows.map((p) => {
    const flags = [];
    if (p.bot) flags.push('<span class="tag">Bot</span>');
    if (p.open_reports) flags.push(`<span class="tag bad" title="Open reports">${p.open_reports} report${p.open_reports > 1 ? "s" : ""}</span>`);
    if (p.warnings) flags.push(`<span class="tag warn" title="Warnings">${p.warnings} warn</span>`);
    if (p.past_bans) flags.push(`<span class="tag bad" title="Earlier bans">${p.past_bans} ban${p.past_bans > 1 ? "s" : ""}</span>`);
    if (p.muted_s || p.mute_until !== undefined) flags.push('<span class="tag warn">Muted</span>');
    if (p.detections) flags.push(`<span class="tag bad">${p.detections} detections</span>`);
    if (p.watched) flags.push('<span class="tag warn">Watched</span>');
    for (const f of p.live_flags || []) flags.push(`<span class="tag ${f === "ban dodger" ? "bad" : "warn"}">${esc(f)}</span>`);
    if (p.suspicion != null) flags.push(susTag(p.suspicion));
    const name = p.pid ? `<a href="#/player/${esc(p.pid)}">${esc(p.name)}</a>` : esc(p.name);
    const acc = p.shots >= 20 && p.hits <= p.shots ? ` title="Accuracy this map: ${Math.round((100 * p.hits) / p.shots)}% of ${p.shots} shots"` : "";
    const team = p.spectator ? "Spectator" : p.team != null ? TEAM[p.team] || "–" : "–";
    const eac = p.bot ? '<span class="dim">–</span>' : p.eac === "protected" ? '<span class="tag ok">Protected</span>' : p.eac ? `<span class="tag warn">${esc(p.eac)}</span>` : '<span class="dim">–</span>';
    const btn = (a, label, perm, danger) => can(perm) ? `<button class="btn btn-small${danger ? " btn-danger" : ""}" data-a="${a}" data-slot="${p.slot}" data-name="${esc(p.name)}" data-pid="${esc(p.pid || "")}">${label}</button>` : "";
    const actions = [p.bot || !p.pid ? "" : btn("punish", "Punish", "punish"), btn("warn", "Warn", "player.warn"), btn(p.muted_s ? "unmute" : "mute", p.muted_s ? "Unmute" : "Mute", "player.mute"),
      btn("move", "Move", "player.move"), btn("kick", "Kick", "player.kick", true), p.bot ? "" : btn("ban", "Ban", "ban.temp", true)].join("");
    return `<tr class="team-${p.spectator ? 0 : p.team || 0}"><td class="pname">${name}<span class="flags">${flags.join("")}</span></td>
      <td>${esc(team)}</td><td class="num">${p.score}</td>${kd ? `<td class="num"${acc}>${p.kills ?? "–"}/${p.deaths ?? "–"}</td>` : ""}
      <td class="num">${p.ping < 0 ? esc(p.state) : p.ping}</td><td>${eac}</td><td class="num">${dur(p.connected_s)}</td>
      <td><div class="row-actions">${actions}</div></td></tr>`;
  }).join("");
  $("#players").innerHTML = head + (body || `<tr><td colspan="8" class="empty">Nobody is on this server.</td></tr>`);
  drawEventBanner(key);
  if (!extra && !$("#legacy-note")) {
    $("#controls").insertAdjacentHTML("afterend", '<p class="dim" id="legacy-note">This server runs a build without the staff commands. Kick, ban, spectate, chat and map control work; warn, mute and team moves arrive with the 0.36.0 server.</p>');
  }
}

async function pollChat(key) {
  try {
    const r = await api("chat?server=" + encodeURIComponent(key || "") + "&after=" + S.chatAfter);
    addChat(r.lines, !key);
  } catch (e) { /* the next poll tries again */ }
}
function addChat(lines, showServer) {
  const log = $("#chat-log");
  if (!log || !lines.length) {
    if (log && !log.children.length) log.innerHTML = '<p class="empty" id="chat-empty">No chat yet.</p>';
    return;
  }
  const empty = $("#chat-empty");
  if (empty) empty.remove();
  const stick = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
  for (const l of lines) {
    S.chatAfter = Math.max(S.chatAfter, l.id);
    const div = document.createElement("div");
    div.className = "chat-line " + (l.kind || "") + (l.flag ? " flagged" : "");
    const srv = showServer ? `<span class="srv">${esc(l.server)}</span>` : "";
    const who = l.pid ? `<a class="who" href="#/player/${esc(l.pid)}">${esc(l.name)}:</a>` : `<span class="who">${esc(l.name)}:</span>`;
    div.innerHTML = `<time>${clock(l.at)}</time>${srv}${who} ${esc(l.text)}${l.flag ? `<span class="flag">${esc(l.flag)}</span>` : ""}`;
    log.appendChild(div);
  }
  while (log.children.length > 400) log.firstChild.remove();
  if (stick) log.scrollTop = log.scrollHeight;
}

function pageChat(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Live</p><h1>Chat, all servers</h1></div></div>
    <div class="panel chat chat-page"><div class="chat-log" id="chat-log"></div>
    ${can("chat.reply") ? '<form class="chat-form" id="chat-form"><select name="server" id="chat-target"></select><input name="text" maxlength="200" placeholder="Reply as staff" autocomplete="off"><button class="btn btn-primary">Send</button></form>' : ""}</div>`;
  S.chatAfter = 0;
  const form = $("#chat-form");
  if (form) {
    loadServers().then((list) => {
      form.server.innerHTML = '<option value="*">Every server</option>' + list.map((s) => `<option value="${esc(s.key)}">${esc(s.name)}</option>`).join("");
      form.server.style.maxWidth = "220px";
    });
    form.onsubmit = async (e) => {
      e.preventDefault();
      const text = form.text.value.trim();
      if (!text) return;
      try { await api("server", { server: form.server.value, action: "chat", text }); form.text.value = ""; } catch (err) { toast(err.message, true); }
    };
  }
  every(() => pollChat(""), 2000, "chat", ["chat"]);
}

/* ------------------------------------------------------------------ actions */
const LENGTHS = [["30m", "30 minutes"], ["2h", "2 hours"], ["12h", "12 hours"], ["1d", "1 day"], ["3d", "3 days"], ["7d", "7 days"], ["30d", "30 days"], ["0", "Permanent"]];

function playerAction(server, slot, name, a, pid) {
  const base = { server, slot, name };
  const send = (extra, label) => async () => {
    const r = await api("action", Object.assign({ action: a }, base, extra));
    toast(label + (r.result ? " · " + r.result.split("\n")[0] : ""), false, r.undo);
    drawServer(server);
  };
  if (a === "punish") return punishDialog({ server, slot, name, pid });
  if (a === "kick") return modal({ title: "Kick " + name, sub: "The player sees the reason and can reconnect.", ok: "Kick", danger: true,
    body: tplSelect("kick", "reason") + '<label>Reason</label><input name="reason" maxlength="100" required placeholder="Team killing">',
    onOk: (f) => send({ reason: f.reason }, "Kicked " + name)() });
  if (a === "warn") return modal({ title: "Warn " + name, sub: "Only this player sees the warning. It is kept on their record.", ok: "Send warning",
    body: tplSelect("warn", "reason") + '<label>Warning</label><input name="reason" maxlength="100" placeholder="Stop spawn camping. Next time it is a kick.">',
    onOk: (f) => send({ reason: f.reason }, "Warned " + name)() });
  if (a === "mute") return modal({ title: "Mute " + name, sub: "Blocks text and voice commands. The mute follows the player across maps and servers.", ok: "Mute",
    body: `<label>Length</label><select name="length">${LENGTHS.filter((l) => l[0] !== "30d").map((l) => `<option value="${l[0]}">${l[1]}</option>`).join("").replace("Permanent", "Until lifted")}</select>
      ${tplSelect("mute", "reason")}<label>Reason</label><input name="reason" maxlength="100" placeholder="Spamming chat">`,
    onOk: (f) => send({ length: f.length, reason: f.reason }, "Muted " + name)() });
  if (a === "unmute") return send({}, "Unmuted " + name)().catch((e) => toast(e.message, true));
  if (a === "move") return modal({ title: "Move " + name, sub: "A living player switches at their next deploy, the same as choosing a team themselves.", ok: "Move",
    body: '<label>Team</label><select name="team"><option value="r">Terrorists</option><option value="b">Specops</option><option value="s">Spectators</option></select>',
    onOk: (f) => send({ team: f.team }, "Moved " + name)() });
  if (a === "ban") return banDialog({ server, slot, name });
}

function banDialog(target) {
  const perm = can("ban.perm");
  const options = LENGTHS.filter((l) => perm || (l[0] !== "0" && ["30m", "2h", "12h", "1d"].includes(l[0])));
  modal({ title: "Ban " + target.name, ok: "Ban", danger: true,
    sub: "The ban holds on every official and pickup server and covers the player's identity, anti-cheat account and address." + (perm ? "" : " Moderators can ban for up to 24 hours."),
    body: `<label>Length</label><select name="length">${options.map((l) => `<option value="${l[0]}"${l[0] === "1d" ? " selected" : ""}>${l[1]}</option>`).join("")}</select>
      ${tplSelect("ban", "reason")}<label>Reason</label><input name="reason" maxlength="100" placeholder="Cheating (aimbot), see report #12">
      <label class="check"><input type="checkbox" name="ip_ban" checked> Also ban the IP address (uncheck for shared connections)</label>
      ${perm ? `<label class="check"><input type="checkbox" name="game"${target.game ? " checked" : ""}> Ban from the whole game: the player cannot start TrueCombat at all, not even offline or on other servers, on any PC or account linked to them</label>` : ""}`,
    onOk: async (f) => {
      const who = target.report ? { report: target.report } : target.pid ? { pid: target.pid } : { server: target.server, slot: target.slot, name: target.name };
      const r = await api("bans", Object.assign({ length: f.length, reason: f.reason, ip_ban: f.ip_ban, game: !!f.game }, who));
      const offline = Object.entries(r.servers).filter(([, v]) => v.startsWith("offline")).map(([k]) => k);
      toast("Banned " + target.name + (r.game ? " from the whole game (" + r.identities + " identities)" : "") + (offline.length ? ". Offline now, applied at the next sync: " + offline.join(", ") : r.game ? "." : " on every server."), false, r.undo);
      if (target.server) drawServer(target.server); else route();
    } });
}

function sayDialog(server) {
  modal({ title: server === "*" ? "Message every server" : "Announce", sub: "Shown in chat to everyone, marked as staff.", ok: "Send",
    body: tplSelect("chat", "text") + '<label>Message</label><input name="text" maxlength="200" placeholder="The server restarts for an update in 5 minutes.">',
    onOk: async (f) => { await api("server", { server, action: "say", text: f.text }); toast("Sent."); } });
}

function mapOptions(s) {
  const maps = new Set([...(S.me.maps || []), ...String(s.rotation || "").split(/\s+/).filter(Boolean)]);
  return [...maps].map((m) => `<option value="${esc(m)}"${m === s.map ? " selected" : ""}>${esc(m)}</option>`).join("");
}

function serverControl(key, c) {
  const s = S.servers.find((x) => x.key === key) || {};
  const players = s.humans ? ` ${s.humans} player${s.humans > 1 ? "s are" : " is"} on the server.` : "";
  if (c === "say") return sayDialog(key);
  if (c === "schedule") return scheduleDialog(key);
  if (c === "event") return eventDialog(key);
  if (c === "map") return modal({ title: "Change map", sub: "Loads the map at once. The current match ends without a result." + players, ok: "Change map",
    body: `<label>Map</label><select name="map">${mapOptions(s)}</select><label>Or type a map name</label><input name="other" placeholder="obj_snow" pattern="[A-Za-z0-9_-]+">`,
    onOk: async (f) => { await api("server", { server: key, action: "map", map: f.other.trim() || f.map }); toast("Map change sent."); } });
  if (c === "nextmap") return modal({ title: "Skip to the next map", sub: "Ends the current map and loads the next one in the rotation." + players, ok: "Skip",
    body: '<p class="muted">The match result on this map is not saved.</p>',
    onOk: async () => { await api("server", { server: key, action: "nextmap" }); toast("Next map loading."); } });
  if (c === "rotation") return modal({ title: "Map rotation", sub: "Applies until the server restarts. Change the server config to keep it.", ok: "Save rotation",
    body: `<label>Maps, in order</label><textarea name="maps">${esc(s.rotation || "")}</textarea>`,
    onOk: async (f) => { await api("server", { server: key, action: "rotation", maps: f.maps }); toast("Rotation updated."); } });
  if (c === "restart") return modal({ title: "Restart the match", sub: "Reloads the current map and resets the score." + players, ok: "Restart match", danger: true,
    body: '<p class="muted">Use this after a broken start or a disconnect wave.</p>',
    onOk: async () => { await api("server", { server: key, action: "restart" }); toast("Match restarting."); } });
}

/* ------------------------------------------------------------------ reports */
function pageReports(main) {
  const state = { status: "open", source: "" };
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Inbox</p><h1>Reports</h1></div></div>
    <div class="tabs" id="r-status"><button class="btn btn-small on" data-s="open">Open</button><button class="btn btn-small" data-s="claimed">In progress</button><button class="btn btn-small" data-s="closed">Closed</button><button class="btn btn-small" data-s="all">All</button></div>
    <div class="tabs" id="r-source"><button class="btn btn-small on" data-k="">Everything</button><button class="btn btn-small" data-k="player">Player reports</button><button class="btn btn-small" data-k="auto">Automatic flags</button><button class="btn btn-small" data-k="appeal">Ban appeals</button><button class="btn btn-small" data-k="bug">Bug reports</button></div>
    <div id="r-list"></div>`;
  const tabs = (id, attr, key) => $(id).onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    for (const x of $(id).children) x.classList.toggle("on", x === b);
    state[key] = b.dataset[attr]; draw();
  };
  tabs("#r-status", "s", "status");
  tabs("#r-source", "k", "source");
  $("#r-list").onclick = async (e) => {
    const demo = e.target.closest("button[data-demo]");
    if (demo) return showDemo(demo);
    const bb = e.target.closest("button[data-bugban]");
    if (bb) return banDialog({ report: +bb.dataset.bugban, name: bb.dataset.name, game: can("ban.perm") });
    const bug = e.target.closest("button[data-bug]");
    if (bug) return bugDetails(+bug.dataset.bug).catch((err) => toast(err.message, true));
    const ap = e.target.closest("button[data-appeal]");
    if (ap) return appealDialog(+ap.dataset.appeal, ap.dataset.decision, ap.dataset.name, draw);
    const cf = e.target.closest("button[data-case-from]");
    if (cf) return newCaseDialog({ report: +cf.dataset.caseFrom, name: cf.dataset.name });
    const b = e.target.closest("button[data-id]"); if (!b) return;
    const set = async (status, resolution) => { await api("reports/update", { id: +b.dataset.id, status, resolution }); toast("Report updated."); draw(); refreshReportCount(); };
    if (b.dataset.do === "close") modal({ title: "Close report", ok: "Close", body: tplSelect("close", "r") + '<label>What was done</label><input name="r" maxlength="200" placeholder="Watched the demo, banned 7 days">', onOk: (f) => set("closed", f.r) });
    else set(b.dataset.do === "claim" ? "claimed" : "open", "").catch((err) => toast(err.message, true));
  };
  async function draw() {
    const r = await api("reports?status=" + state.status + "&source=" + state.source).catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    $("#r-list").innerHTML = r.reports.map(reportCard).join("") || '<p class="empty">Nothing here. Good.</p>';
  }
  every(draw, 20000, "reports", ["reports", "alert", "action"]);
}

function reportCard(r) {
  const d = r.data || {};
  const status = r.status === "open" ? '<span class="tag bad">Open</span>' : r.status === "claimed" ? `<span class="tag warn">${esc(r.claimed_by || "In progress")}</span>` : '<span class="tag ok">Closed</span>';
  const buttons = [r.status !== "claimed" && r.status !== "closed" ? `<button class="btn btn-small" data-id="${r.id}" data-do="claim">Take it</button>` : "",
    r.source === "appeal" ? "" : r.status !== "closed" ? `<button class="btn btn-small" data-id="${r.id}" data-do="close">Close</button>` : `<button class="btn btn-small" data-id="${r.id}" data-do="reopen">Reopen</button>`,
    can("cases") && r.source !== "bug" ? `<button class="btn btn-small" data-case-from="${r.id}" data-name="${esc(r.target_name || "")}">Open a case</button>` : ""].join("");
  if (r.source === "appeal") {
    const ban = d.ban || {};
    const decide = r.status !== "closed" && can("appeals.answer") ? `<button class="btn btn-small" data-appeal="${esc(d.appeal_id)}" data-decision="accept" data-name="${esc(r.target_name)}">Accept, lift ban</button><button class="btn btn-small btn-danger" data-appeal="${esc(d.appeal_id)}" data-decision="deny" data-name="${esc(r.target_name)}">Deny</button>` : "";
    const name = r.target_pid ? `<a href="#/player/${esc(r.target_pid)}">${esc(r.target_name)}</a>` : esc(r.target_name);
    return `<div class="panel"><div class="head"><div><div class="tags">${status}<span class="tag staff">Ban appeal</span></div>
      <h2>${name}</h2><span class="muted">Ban #${esc(ban.id)}: ${esc(ban.reason)} · by ${esc(ban.by)} · ${esc(until(ban.expires))} · appealed ${when(r.received)}</span></div>
      <div class="actions">${decide}${r.status === "open" ? buttons : ""}</div></div>
      <p class="text-block">“${esc(d.text)}”</p>${d.contact ? `<p class="muted">Contact: ${esc(d.contact)}</p>` : ""}
      ${r.resolution ? `<p class="muted">${esc(r.resolution)}</p>` : ""}</div>`;
  }
  if (r.source === "bug") {
    const who = d.name ? (r.target_pid ? `<a href="#/player/${esc(r.target_pid)}">${esc(d.name)}</a>` : esc(d.name)) : "";
    const facts = [
      d.map ? ["Map", esc(d.map) + (d.pos ? ` <span class="dim">at ${d.pos.map((n) => esc(n)).join(", ")}</span>` : "")] : null,
      d.server ? ["Server", esc(d.server) + (d.server_name ? "" : d.server_label ? ` <span class="dim">· ${esc(d.server_label)} (not one of ours)</span>` : "")] : (d.format ? ["Server", "Not on a server"] : null),
      d.build ? ["Build", esc(d.build) + (d.renderer ? ` <span class="dim">· ${esc(d.renderer)}</span>` : "") + (d.protocol ? ` <span class="dim">· ${esc(d.protocol)}</span>` : "")] : null,
      d.ping != null || d.fps != null ? ["Ping, fps", `${d.ping ?? "–"} ms · ${d.fps ?? "–"} fps`] : null,
      d.time ? ["Taken", when(d.time)] : null,
      d.match ? ["Match", esc(d.match)] : null,
      d.puid ? ["Anti-cheat id", `<span class="mono">${esc(d.puid)}</span>`] : null,
    ].filter(Boolean).map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
    const extra = (d.has_console ? `<button class="btn btn-small" data-bug="${r.id}">Console and hardware</button>` : "") +
      (can("ban.temp") ? `<button class="btn btn-small btn-danger" data-bugban="${r.id}" data-name="${esc(d.name || r.target_name || "this player")}">Ban sender</button>` : "");
    return `<div class="panel"><div class="head"><div><div class="tags">${status}<span class="tag">${esc(d.category || "Bug")}</span>${d.server_name ? `<span class="tag">${esc(d.server_name)}</span>` : ""}</div>
      <h2>${esc(d.summary || "Bug report")}</h2><span class="muted">${who ? "From " + who + " · " : ""}received ${when(r.received)}</span></div><div class="actions">${buttons}</div></div>
      <div class="report-body">${esc(d.text || "")}</div>
      ${d.shot ? `<a class="bugshot" href="/api/reports/bugshot?id=${r.id}" target="_blank" rel="noopener"><img src="/api/reports/bugshot?id=${r.id}" alt="Screenshot taken with the report" loading="lazy"></a>` : ""}
      ${facts ? `<dl class="kv">${facts}</dl>` : ""}${extra ? `<div class="tags">${extra}</div>` : ""}
      ${r.resolution ? `<p class="muted">Resolution: ${esc(r.resolution)}</p>` : ""}</div>`;
  }
  const who = d.reported || {}, by = d.reporter || {};
  const acc = who.shots ? Math.round((100 * who.hits) / who.shots) + "%" : "–";
  const name = r.target_pid ? `<a href="#/player/${esc(r.target_pid)}">${esc(r.target_name)}</a>` : esc(r.target_name);
  return `<div class="panel"><div class="head"><div><div class="tags">${status}<span class="tag${r.source === "auto" ? " bad" : ""}">${r.source === "auto" ? "Automatic flag" : "Player report"}</span><span class="tag">${esc(r.server)}</span></div>
      <h2>${name}</h2><span class="muted">${esc(d.map || "")} · ${when(r.received)}${r.source === "auto" ? "" : " · reported by " + esc(by.name || "unknown")}</span></div>
      <div class="actions">${buttons}</div></div>
    <p>“${esc(d.reason || "No reason given")}”</p>
    <div class="tags"><button class="btn btn-small" data-demo="${r.id}">Server demo</button><span class="dim small" id="demo-${r.id}"></span></div>
    <dl class="kv"><dt>This map</dt><dd>${who.kills ?? 0} kills · ${who.deaths ?? 0} deaths · ${who.team_kills ?? 0} team kills</dd>
      <dt>Accuracy</dt><dd>${acc}${who.headshots != null ? " · " + who.headshots + " headshots" : ""}</dd>
      ${r.resolution ? `<dt>Resolution</dt><dd>${esc(r.resolution)}</dd>` : ""}</dl></div>`;
}

async function bugDetails(id) {
  const d = (await api("reports/bug?id=" + id)).report.data;
  const hw = d.hw ? Object.entries(d.hw).map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("") : "";
  modal({ title: "Console and hardware", sub: d.summary || "Bug report", ok: "Close",
    body: (hw ? `<dl class="kv">${hw}</dl>` : "") + `<label>Last console lines</label><div class="report-body console">${esc(d.console || "None sent.")}</div>`,
    onOk: () => {} });
}

/* ------------------------------------------------------------------ players */
function pagePlayers(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Lookup</p><h1>Players</h1></div></div>
    <form class="search" id="lookup"><input name="q" placeholder="Name, player id${can("lookup.ip") ? " or IP address" : ""}" autocomplete="off"><button class="btn btn-primary">Search</button></form>
    <div class="panel" id="results"><p class="empty">Search by any name a player has used on our servers, in a bug report or when starting the game.</p></div>`;
  const form = $("#lookup");
  const last = sessionStorage.getItem("lookup") || "";
  form.q.value = last;
  form.onsubmit = async (e) => {
    e.preventDefault();
    const q = form.q.value.trim();
    sessionStorage.setItem("lookup", q);
    if (q.length < 2) return;
    const r = await api("lookup?q=" + encodeURIComponent(q)).catch((err) => { toast(err.message, true); return null; });
    if (!r) return;
    $("#results").innerHTML = r.players.length ? `<table><tr><th>Player</th><th>Also known as</th><th>Last seen</th><th></th></tr>${r.players.map((p) => `
      <tr><td class="pname"><a href="#/player/${esc(p.pid)}">${esc(p.names[0] || p.pid)}</a> <span class="mono dim">${esc(p.pid)}</span></td>
      <td>${esc(p.names.slice(1).join(", "))}</td><td>${p.last_seen ? ago(p.last_seen) : '<span class="dim">stats only</span>'}</td>
      <td>${p.game_banned ? '<span class="tag bad">Banned from the game</span>' : p.banned ? '<span class="tag bad">Banned</span>' : ""}${p.seen_in && !p.last_seen ? ` <span class="dim">${esc(p.seen_in)}</span>` : ""}</td></tr>`).join("")}</table>` : '<p class="empty">No player matches that.</p>';
  };
  if (last.length >= 2) form.requestSubmit();
}

async function pagePlayer(main, pid) {
  let p;
  try { p = await api("player/" + encodeURIComponent(pid)); } catch (e) { main.innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
  const name = (p.names[0] && p.names[0].name) || pid;
  const st = p.stats;
  const activeBan = p.bans.find((b) => b.active);
  main.innerHTML = `<div class="head"><div><p class="eyebrow"><a href="#/players">Players</a></p><h1>${esc(name)}</h1>
      <div class="tags">${p.online.map((o) => `<a class="tag ok" href="#/server/${esc(o.server)}">Online on ${esc(o.server)}</a>`).join("")}
      ${activeBan ? `<span class="tag bad">${activeBan.game ? "Banned from the game" : "Banned"} · ${esc(until(activeBan.expires))}</span>` : ""}<span class="tag mono">${esc(pid)}</span></div></div>
    <div class="actions"><a class="btn" href="${esc(p.profile_url)}" target="_blank" rel="noopener">Public profile</a>
      ${can("watch") ? `<button class="btn" id="p-watch">${p.watch ? "Stop watching" : "Watch"}</button>` : ""}
      ${can("cases") ? '<button class="btn" id="p-case">Open a case</button>' : ""}
      ${can("punish") && !activeBan ? '<button class="btn" id="p-punish">Punish</button>' : ""}
      ${can("ban.temp") && !activeBan ? '<button class="btn btn-danger" id="p-ban">Ban</button>' : ""}</div></div>
    ${p.watch ? `<div class="banner"><span>On the watchlist: ${esc(p.watch.reason || "no reason given")} · ${esc(p.watch.by_name)}, ${when(p.watch.created)}</span></div>` : ""}
    <div class="grid grid-2"><div>
      <div class="panel"><div class="head"><h3>Timeline</h3><div class="tabs" id="p-tl-tabs"><button class="btn btn-small on" data-f="">All</button><button class="btn btn-small" data-f="mod">Moderation</button><button class="btn btn-small" data-f="report">Reports</button><button class="btn btn-small" data-f="session">Play sessions</button></div></div>
        <ul class="tl" id="p-tl"><li class="dim">Loading…</li></ul><p class="tags"><button class="btn btn-small" id="p-tl-more" hidden>Show more</button></p></div>
      <div class="panel"><h3>Recent matches</h3><div class="table-wrap">${p.matches.length ? `<table><tr><th>Ended</th><th>Map</th><th class="num">K</th><th class="num">D</th><th class="num">HS</th><th>Result</th></tr>${p.matches.map((m) => `<tr><td>${esc(String(m.ended || "").replace("T", " ").slice(0, 16))}</td><td>${esc(m.map)}</td><td class="num">${m.kills}</td><td class="num">${m.deaths}</td><td class="num">${m.headshots}</td><td>${m.won ? "Won" : "Lost"}</td></tr>`).join("")}</table>` : '<p class="empty">No stats-tracked matches yet.</p>'}</div></div>
      <div class="panel"><h3>Recent chat</h3><div class="chat-log" id="p-chat"></div></div>
    </div><div>
      ${suspicionPanel(p.suspicion)}
      <div class="panel"><h3>Identity</h3><dl class="kv">
        <dt>First seen</dt><dd>${p.first_seen ? when(p.first_seen) : "–"}</dd><dt>Last seen</dt><dd>${p.last_seen ? ago(p.last_seen) : "–"}</dd>
        <dt>Servers</dt><dd>${esc(p.servers.join(", ") || "–")}</dd>
        <dt>Anti-cheat id</dt><dd class="mono">${esc(p.puids.join(", ") || "–")}</dd>
        <dt>Discord</dt><dd>${p.discord == null ? '<span class="dim">link list not available</span>' : p.discord.length ? p.discord.map((x) => `${esc(x.name || "")} <span class="mono dim">${esc(x.discord_id)}</span>`).join("<br>") : '<span class="dim">not linked</span>'}</dd>
        ${st ? `<dt>Rating</dt><dd>${st.ranked ? esc(st.rating) + (st.position ? " · #" + esc(st.position) : "") : "not ranked yet"} · ${esc(st.matches)} matches</dd><dt>Career</dt><dd>${esc(st.kills)} K · ${esc(st.deaths)} D · ${esc(st.teamKills ?? 0)} TK</dd>` : ""}
      </dl></div>
      ${p.alts && p.alts.length ? `<div class="panel"><h3>Possible other accounts</h3><ul class="list">${p.alts.map((a) => `<li><a href="#/player/${esc(a.pid)}">${esc(a.name)}</a> ${a.banned ? '<span class="tag bad">Banned</span>' : ""} <span class="dim">· same ${esc(a.why)}</span></li>`).join("")}</ul></div>` : ""}
      ${p.flags && p.flags.length ? `<div class="panel"><h3>Flags</h3><ul class="list">${p.flags.slice(0, 15).map((f) => `<li><span class="tag ${f.kind === "ban dodger" ? "bad" : "warn"}">${esc(f.kind)}</span> ${esc(f.detail)} <span class="dim">· ${esc(f.server)} · ${when(f.at)}</span></li>`).join("")}</ul></div>` : ""}
      <div class="panel"><h3>Names used</h3><ul class="list">${p.names.map((n) => `<li>${esc(n.name)} <span class="dim">· ${ago(n.last_seen)}</span></li>`).join("") || '<li class="dim">None recorded.</li>'}</ul></div>
      ${p.ips ? `<div class="panel"><h3>Addresses (admin only)</h3><ul class="list">${p.ips.map((i) => `<li class="mono">${esc(i.ip)} <span class="dim">· ${ago(i.last_seen)}</span></li>`).join("") || '<li class="dim">None.</li>'}</ul>
        ${p.shared_ip && p.shared_ip.length ? `<p class="muted">Other players seen on these addresses: ${p.shared_ip.map((x) => `<a class="mono" href="#/player/${esc(x)}">${esc(x)}</a>`).join(", ")}</p>` : ""}</div>` : ""}
      ${can("cases") ? '<div class="panel"><h3>Cases</h3><ul class="list" id="p-cases"><li class="dim">Loading…</li></ul></div>' : ""}
      ${can("evidence") ? '<div class="panel" id="p-evidence"></div>' : ""}
      <div class="panel"><h3>Staff notes</h3><ul class="list">${p.notes.map((n) => `<li>${esc(n.text)} <div class="dim">${esc(n.by_name)} · ${when(n.created)}</div></li>`).join("") || '<li class="dim">No notes yet.</li>'}</ul>
        <form id="p-note" class="chat-form"><input name="text" maxlength="1000" placeholder="Add a note for other staff"><button class="btn">Add</button></form></div>
    </div></div>`;
  drawTimeline(pid);
  if (can("cases")) api("cases?pid=" + encodeURIComponent(pid)).then((r) => {
    $("#p-cases").innerHTML = r.cases.map((c) => `<li><a href="#/case/${c.id}">#${c.id} ${esc(c.title)}</a> ${c.status === "open" ? '<span class="tag warn">Open</span>' : '<span class="tag ok">Closed</span>'} <span class="dim">· ${esc(c.assignee || "nobody")} · ${ago(c.updated)}</span></li>`).join("") || '<li class="dim">No cases.</li>';
  }).catch(() => {});
  if (can("evidence")) evidencePanel($("#p-evidence"), { pid });
  const pc = $("#p-case");
  if (pc) pc.onclick = () => newCaseDialog({ pid, name });
  const chat = $("#p-chat");
  chat.innerHTML = p.chat.map((l) => `<div class="chat-line ${esc(l.kind)}"><time>${when(l.at)}</time><span class="srv">${esc(l.server)}</span><span class="who">${esc(l.name)}:</span> ${esc(l.text)}</div>`).join("") || '<p class="empty">No chat recorded.</p>';
  $("#p-note").onsubmit = async (e) => {
    e.preventDefault();
    const text = e.target.text.value.trim();
    if (!text) return;
    try { await api("notes", { pid, text }); route(); } catch (err) { toast(err.message, true); }
  };
  const ban = $("#p-ban");
  if (ban) ban.onclick = () => banDialog({ pid, name });
  const pun = $("#p-punish");
  if (pun) pun.onclick = () => punishDialog({ pid, name });
  const watch = $("#p-watch");
  if (watch) watch.onclick = () => {
    if (p.watch) return api("watchlist", { pid, remove: true }).then(() => { toast("Removed from the watchlist."); route(); }).catch((e) => toast(e.message, true));
    modal({ title: "Watch " + name, sub: "Staff get an alert in Discord and in the portal whenever this player joins a server.", ok: "Watch",
      body: '<label>Why</label><input name="reason" maxlength="200" placeholder="Suspicious flicks on Snow, see report #31">',
      onOk: async (f) => { await api("watchlist", { pid, name, reason: f.reason }); toast("On the watchlist."); route(); } });
  };
}

/* ------------------------------------------------------------------ bans */
function pageBans(main) {
  let show = "active";
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Enforcement</p><h1>Bans</h1></div>
    <div class="actions">${can("ban.temp") ? '<button class="btn btn-danger" id="b-new">Ban a player</button>' : ""}${can("ban.remove") ? '<button class="btn" id="b-sync">Check every server now</button><button class="btn" id="b-server">Bans set in game</button>' : ""}</div></div>
    <div class="tabs" id="b-tabs"><button class="btn btn-small on" data-v="active">Active</button><button class="btn btn-small" data-v="all">History</button></div>
    <div class="panel table-wrap" id="b-list"></div><div id="b-extra"></div>`;
  $("#b-tabs").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#b-tabs").children) x.classList.toggle("on", x === b); show = b.dataset.v; draw(); };
  const nb = $("#b-new");
  if (nb) nb.onclick = () => findToBan();
  const sync = $("#b-sync");
  if (sync) sync.onclick = async () => {
    try { const r = await api("bans/sync", {}); toast(Object.entries(r.result).map(([k, v]) => k + ": " + v).join(" · ")); } catch (e) { toast(e.message, true); }
  };
  const srv = $("#b-server");
  if (srv) srv.onclick = async () => {
    const r = await api("bans/server").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    $("#b-extra").innerHTML = Object.entries(r.servers).map(([k, list]) => `<div class="panel"><h3>${esc(k)}</h3>${list.error ? `<p class="error">${esc(list.error)}</p>` : list.length ? `<table><tr><th>#</th><th>Name</th><th>Reason</th><th>Left</th></tr>${list.map((b) => `<tr><td>${b.number}</td><td>${esc(b.name)}</td><td>${esc(b.reason)}</td><td>${b.minutes_left ? b.minutes_left + " min" : "permanent"}</td></tr>`).join("")}</table>` : '<p class="empty">No bans on this server.</p>'}</div>`).join("");
  };
  $("#b-list").onclick = (e) => {
    const u = e.target.closest("button[data-undo]");
    if (u) return api("undo", { id: +u.dataset.undo }).then((r) => { toast(r.message); draw(); }).catch((err) => toast(err.message, true));
    const b = e.target.closest("button[data-lift]"); if (!b) return;
    modal({ title: "Lift ban on " + b.dataset.name, sub: "Removes the ban from every server.", ok: "Lift ban",
      body: '<label>Why</label><input name="reason" maxlength="200" placeholder="Appeal accepted">',
      onOk: async (f) => { await api("bans/lift", { id: +b.dataset.lift, reason: f.reason }); toast("Ban lifted."); draw(); } });
  };
  async function draw() {
    const r = await api("bans?show=" + show).catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    $("#b-list").innerHTML = r.bans.length ? `<table><tr><th>Player</th><th>Reason</th><th>By</th><th>Since</th><th>Status</th><th></th></tr>${r.bans.map((b) => `
      <tr><td class="pname">${b.pid ? `<a href="#/player/${esc(b.pid)}">${esc(b.name)}</a>` : esc(b.name)}${b.game ? ` <span class="tag bad" title="${b.identities} identities covered">Whole game</span>` : ""}</td><td>${esc(b.reason)}</td><td>${esc(b.by_name)}</td><td>${when(b.created)}</td>
      <td>${b.active ? `<span class="tag bad">${esc(until(b.expires))}</span>` : `<span class="tag">Lifted${b.lifted_by ? " · " + esc(b.lifted_by) : ""}</span>`}</td>
      <td><div class="row-actions">${b.active && b.undo ? `<button class="btn btn-small" data-undo="${b.undo}">Undo</button>` : ""}${b.active && can("ban.remove") ? `<button class="btn btn-small" data-lift="${b.id}" data-name="${esc(b.name)}">Lift</button>` : ""}</div></td></tr>`).join("")}</table>` : '<p class="empty">No bans.</p>';
  }
  every(draw, 30000, "bans", ["action"]);
}

function findToBan() {
  modal({ title: "Ban a player", sub: "Finds anyone the portal has seen: on our servers, in a bug report or starting the game. Search by name, player id, GUID or anti-cheat id.", ok: "Close",
    body: '<div class="search"><input id="fb-q" placeholder="Name or id" autocomplete="off"><button type="button" class="btn" id="fb-go">Search</button></div><div id="fb-list" class="list"></div>',
    onOk: () => {} });
  const input = $("#fb-q");
  input.focus();
  input.onkeydown = (e) => { if (e.key === "Enter") { e.preventDefault(); find(); } };
  $("#fb-go").onclick = () => find();
  const find = async () => {
    const q = input.value.trim();
    if (q.length < 2) return;
    const r = await api("lookup?q=" + encodeURIComponent(q)).catch((err) => { toast(err.message, true); return null; });
    if (!r) return;
    $("#fb-list").innerHTML = r.players.length ? r.players.map((p) => `<div class="row-actions"><span class="pname">${esc(p.names[0] || p.pid)} <span class="mono dim">${esc(p.pid)}</span> ${p.game_banned ? '<span class="tag bad">Banned from the game</span>' : p.banned ? '<span class="tag bad">Banned</span>' : ""}</span>${p.game_banned ? "" : `<button class="btn btn-small btn-danger" data-pid="${esc(p.pid)}" data-name="${esc(p.names[0] || p.pid)}">Ban</button>`}</div>`).join("") : '<p class="empty">Nobody matches that.</p>';
  };
  $("#fb-list").onclick = (e) => {
    const b = e.target.closest("button[data-pid]"); if (!b) return;
    closeModal();
    banDialog({ pid: b.dataset.pid, name: b.dataset.name, game: can("ban.perm") });
  };
}

/* ------------------------------------------------------------------ audit */
function pageAudit(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Accountability</p><h1>Audit log</h1></div>
    <form class="search" id="a-form"><input name="q" placeholder="Staff member, player, action"><button class="btn">Filter</button></form></div>
    <div class="panel table-wrap" id="a-list"></div>`;
  const draw = async () => {
    const q = $("#a-form").q.value.trim();
    const r = await api("audit" + (q ? "?q=" + encodeURIComponent(q) : "")).catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    $("#a-list").innerHTML = r.entries.length ? `<table><tr><th>When</th><th>Staff</th><th>Action</th><th>Server</th><th>Target</th><th>Detail</th></tr>${r.entries.map((a) => `
      <tr><td>${when(a.at)}</td><td>${esc(a.staff)} <span class="role">${esc(a.role)}</span></td><td>${a.ok ? "" : '<span class="tag bad">failed</span> '}${esc(a.action)}</td>
      <td>${esc(a.server)}</td><td>${a.target_pid ? `<a href="#/player/${esc(a.target_pid)}">${esc(a.target)}</a>` : esc(a.target)}</td><td>${esc(a.detail)}</td></tr>`).join("")}</table>` : '<p class="empty">Nothing logged yet.</p>';
  };
  $("#a-form").onsubmit = (e) => { e.preventDefault(); draw(); };
  every(draw, 30000, "audit");
}

/* ------------------------------------------------------------------ staff */
function pageStaff(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Access</p><h1>Staff</h1>
    <p class="muted">Discord roles grant access automatically. Use this list to add someone without the role, raise them to admin, or shut someone out.</p></div>
    <div class="actions"><button class="btn btn-primary" id="s-add">Add or change</button></div></div><div class="panel table-wrap" id="s-list"></div>
    <div class="head"><div><h2>Staff keys in game</h2><p class="muted">Each staff member gets their own key under their name, bottom left. A key stops working when it is revoked, when someone loses staff access, or after a long time without signing in to the portal.</p></div></div>
    <div class="panel table-wrap" id="s-keys"></div>`;
  const edit = (row = {}) => modal({ title: row.discord_id ? "Change " + (row.name || row.discord_id) : "Add staff", ok: "Save",
    sub: S.me.role === "owner" ? "" : "Only the owner can make or change admins.",
    body: `<label>Discord user id</label><input name="discord_id" value="${esc(row.discord_id || "")}" placeholder="183662139000000000" inputmode="numeric">
      <label>Name (for this list)</label><input name="name" value="${esc(row.name || "")}">
      <label>Access</label><select name="role"><option value="trial">Trial moderator</option><option value="moderator">Moderator</option>${S.me.role === "owner" ? '<option value="admin">Admin</option>' : ""}<option value="discord">Follow Discord roles</option><option value="revoked">No access, even with the Discord role</option></select>
      <label>Note</label><input name="note" value="${esc(row.note || "")}" placeholder="Trial moderator until December">`,
    onOk: async (f) => { await api("staff", f); toast("Saved."); draw(); } });
  $("#s-add").onclick = () => edit();
  $("#s-list").onclick = (e) => {
    const b = e.target.closest("button[data-i]"); if (b) return edit(draw.rows[+b.dataset.i]);
    const r = e.target.closest("button[data-rights]"); if (r) rightsDialog(r.dataset.rights, draw).catch((err) => toast(err.message, true));
  };
  $("#s-keys").onclick = (e) => {
    const b = e.target.closest("button[data-revoke]"); if (!b) return;
    modal({ title: "Revoke staff key", sub: b.dataset.name, ok: "Revoke", danger: true, body: "<p>Their staff badge stops on our servers right away. They can make a new key while they still have portal access.</p>",
      onOk: async () => { await api("staffkey/revoke", { id: b.dataset.revoke }); toast("Key revoked."); drawKeys(); } });
  };
  async function drawKeys() {
    const r = await api("staffkeys").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    const certs = r.cert_root ? `<p class="small"><span class="tag ok">Certificates on</span> Root ${esc(r.cert_root)} signs a ${r.cert_days}-day certificate for every active key, so the badge works on any server running 0.38.0 or later.</p>`
      : '<p class="small"><span class="tag">Certificates off</span> <span class="dim">No certificate root is set up yet. Until then the badge works on servers that read the portal key list.</span></p>';
    $("#s-keys").innerHTML = certs + (r.keys.length ? `<table><tr><th>Name</th><th>Key</th><th>Made</th><th>State</th><th></th></tr>${r.keys.map((k) => `
      <tr><td>${esc(k.name)}</td><td class="mono">${esc(k.id)}</td><td>${when(k.created)}</td><td>${k.active ? '<span class="tag ok">Active</span>' : `<span class="tag bad">Not active</span> <span class="dim small">no sign-in for ${r.idle_days} days</span>`}</td>
      <td><button class="btn btn-small btn-danger" data-revoke="${esc(k.id)}" data-name="${esc(k.name)}">Revoke</button></td></tr>`).join("")}</table>` : '<p class="empty">No staff keys made in the portal yet.</p>');
  }
  drawKeys();
  async function draw() {
    const r = await api("staff").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    draw.rows = r.staff;
    $("#s-list").innerHTML = `<table><tr><th>Name</th><th>Discord id</th><th>Access</th><th>Last sign-in</th><th>Note</th><th></th></tr>${r.staff.map((s, i) => `
      <tr><td>${esc(s.name || "–")}</td><td class="mono">${esc(s.discord_id)}</td><td>${s.role ? `<span class="role">${esc(s.role)}</span>` : '<span class="dim">Discord role</span>'}</td>
      <td>${s.last_login ? ago(s.last_login) : "never"}</td><td>${esc(s.note || "")}</td><td>${s.role === "owner" ? "" : `<button class="btn btn-small" data-i="${i}">Change</button> <button class="btn btn-small" data-rights="${esc(s.discord_id)}">Rights</button>`}${(s.perms_add && s.perms_add !== "[]") || (s.perms_remove && s.perms_remove !== "[]") ? ' <span class="tag staff">Custom</span>' : ""}</td></tr>`).join("")}</table>`;
  }
  draw();
}

/* ------------------------------------------------------------------ health */
function pageHealth(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Infrastructure</p><h1>Health</h1></div></div>
    <div class="cards" id="h-top"></div><div class="panel table-wrap" id="h-units"></div>
    ${can("backup") ? '<div class="panel" id="h-backup"></div>' : ""}`;
  const bk = $("#h-backup");
  const drawBackup = async () => {
    const b = await api("backup").catch((e) => ({ error: e.message }));
    bk.innerHTML = `<div class="head"><div><h3>Database snapshot</h3><p class="dim small">Every night at ${esc(b.hour_utc || "04:20")} UTC the portal writes a copy of its database without sign-in sessions. The nightly off-site backup encrypts it and stores it in the private backup repository.</p></div>
      <div class="actions"><button class="btn btn-small" id="bk-now">Make a snapshot now</button></div></div>
      ${b.at ? `<dl class="kv"><dt>Last snapshot</dt><dd>${b.ok ? '<span class="tag ok">OK</span>' : '<span class="tag bad">Failed</span>'} ${when(b.at)} <span class="dim">(${ago(b.at)})</span></dd>
        ${b.ok ? `<dt>Size</dt><dd>${(b.size / 1048576).toFixed(2)} MB · ${b.tables} tables</dd><dt>SHA-256</dt><dd class="mono">${esc(String(b.sha256 || "").slice(0, 16))}…</dd>` : `<dt>Problem</dt><dd class="error">${esc(b.error || "")}</dd>`}</dl>`
        : `<p class="empty">${esc(b.error || "No snapshot yet.")}</p>`}`;
    $("#bk-now").onclick = async () => { try { const r = await api("backup", {}); toast(r.ok ? "Snapshot written." : "Snapshot failed: " + r.error, !r.ok); drawBackup(); } catch (e) { toast(e.message, true); } };
  };
  if (bk) drawBackup();
  $("#h-units").onclick = (e) => {
    const b = e.target.closest("button[data-restart]"); if (!b) return;
    const key = b.dataset.restart;
    const s = S.servers.find((x) => x.key === key) || {};
    modal({ title: "Restart " + (s.name || key), danger: true, ok: "Restart service",
      sub: "Stops and starts the game server process. Everyone on it is disconnected and reconnects by themselves." + (s.humans ? " " + s.humans + " players are on it right now." : ""),
      body: s.humans ? '<label class="check"><input type="checkbox" name="confirm_players"> Restart with players on the server</label>' : "",
      onOk: async (f) => { await api("health/restart", { server: key, confirm_players: !!f.confirm_players }); toast("Restarted."); draw(); } });
  };
  async function draw() {
    let h;
    try { [h] = await Promise.all([api("health"), loadServers()]); } catch (e) { toast(e.message, true); return; }
    const memUsed = h.mem_total_mb ? 100 - Math.round((100 * h.mem_available_mb) / h.mem_total_mb) : 0;
    const diskUsed = h.disk_total_gb ? 100 - Math.round((100 * h.disk_free_gb) / h.disk_total_gb) : 0;
    const load = h.load ? Math.round((100 * h.load[0]) / (h.cpus || 1)) : 0;
    const level = (v) => (v > 90 ? " bad" : v > 75 ? " warn" : "");
    const tile = (label, value, pct, note) => `<div class="card"><div class="meta">${label}</div><div class="stat">${value}</div><div class="bar${level(pct)}"><span data-w="${Math.min(100, pct)}"></span></div><div class="dim">${note}</div></div>`;
    $("#h-top").innerHTML = [
      tile("CPU load", h.load ? h.load[0].toFixed(2) : "–", load, (h.cpus || "?") + " cores · 5 min " + (h.load ? h.load[1].toFixed(2) : "–")),
      tile("Memory", memUsed + "%", memUsed, (h.mem_available_mb || 0) + " MB free of " + (h.mem_total_mb || 0)),
      tile("Disk", diskUsed + "%", diskUsed, (h.disk_free_gb || 0) + " GB free"),
      tile("VPS uptime", h.uptime_s ? Math.floor(h.uptime_s / 86400) + "d" : "–", 0, "portal " + esc(h.portal_version)),
    ].join("");
    for (const span of document.querySelectorAll("#h-top .bar span")) span.style.width = span.dataset.w + "%";
    $("#h-units").innerHTML = `<table><tr><th>Service</th><th>State</th><th>Since</th><th class="num">Memory</th><th class="num">Restarts</th><th>Problems, 24 h</th><th></th></tr>${h.services.map((u) => {
      const srv = S.servers.find((x) => x.key === u.key);
      const state = u.state === "active" ? '<span class="tag ok">Running</span>' : u.state === "unknown" ? '<span class="tag">Unknown</span>' : `<span class="tag bad">${esc(u.state)}</span>`;
      return `<tr><td><b>${esc(u.name)}</b><div class="mono dim">${esc(u.unit)}</div></td><td>${state}${srv ? (srv.online ? ' <span class="tag ok">Answering</span>' : ' <span class="tag bad">Not answering</span>') : ""}</td>
        <td>${esc(u.since || "")}</td><td class="num">${u.memory_mb != null ? u.memory_mb + " MB" : "–"}</td><td class="num">${u.restarts ?? "–"}</td>
        <td>${u.problems_24h ? `<span class="tag warn">${u.problems_24h}</span> <span class="dim">${esc(u.last_problem)}</span>` : '<span class="dim">None</span>'}</td>
        <td>${srv && can("health.restart") ? `<button class="btn btn-small btn-danger" data-restart="${esc(u.key)}">Restart</button>` : ""}</td></tr>`;
    }).join("")}</table>`;
  }
  every(draw, 15000, "health");
}

/* ------------------------------------------------------------------ round two: shared pieces */
function suspicionPanel(sus) {
  if (!sus) return "";
  const cls = sus.score >= 60 ? "high" : sus.score >= 25 ? "mid" : "";
  return `<div class="panel"><h3>Suspicion score</h3><div class="score ${cls}">${sus.score}<small class="muted"> / 100</small></div>
    <p class="dim small">${sus.live ? "Live, from this session" : "Last seen " + ago(sus.updated)}${sus.peak > sus.score ? " · highest " + sus.peak : ""}. A pointer to look closer, never proof on its own.</p>
    <ul class="list">${sus.reasons.map((r) => `<li>${esc(r)}</li>`).join("") || '<li class="dim">Nothing stands out.</li>'}</ul></div>`;
}

async function punishDialog(t) {
  let r;
  try { r = await api("punish/next?pid=" + encodeURIComponent(t.pid)); } catch (e) { return toast(e.message, true); }
  const online = t.server != null;
  const rows = r.steps.map((x) => {
    const ban = x.step.startsWith("ban");
    const off = !online && !ban;
    const steps = x.steps.map((label, i) => (i === x.index ? `<b>${esc(label)}</b>` : esc(label))).join(" → ");
    return `<li><div><b>${esc(x.label)}</b><div class="steps">${steps}</div><div class="dim small">${x.earlier ? x.earlier + " earlier in " + x.days + " days" : "first time"}${off ? " · player must be online for this step" : ""}</div></div>
      <button type="button" class="btn btn-small${ban ? " btn-danger" : ""}" data-off="${esc(x.offence)}"${off ? " disabled" : ""}>${esc(x.action)}</button></li>`;
  }).join("");
  modal({ title: "Punish " + t.name, sub: "Every offence climbs one step for each earlier punishment for it. Pick the offence, the ladder picks the step.", ok: "Close",
    body: `<label>Note for the record (optional)</label><input name="note" maxlength="100" placeholder="Killed three teammates at spawn"><ul class="ladder">${rows}</ul>`,
    onOk: async () => {} });
  $("#modal-ok").hidden = true;
  $("#modal-body").onclick = async (e) => {
    const b = e.target.closest("button[data-off]"); if (!b) return;
    b.disabled = true;
    const note = $("#modal-body").querySelector('[name="note"]').value;
    try {
      const res = await api("punish", Object.assign({ offence: b.dataset.off, note }, online ? { server: t.server, slot: t.slot, name: t.name } : { pid: t.pid }));
      closeModal();
      $("#modal-ok").hidden = false;
      toast(`${t.name}: ${res.action} (step ${res.step} of ${res.of})`, false, res.audit_id);
      if (online) drawServer(t.server); else route();
    } catch (err) { $("#modal-error").textContent = err.message; $("#modal-error").hidden = false; b.disabled = false; }
  };
}

function eventDialog(key) {
  const ev = S.events[key];
  if (ev) {
    return modal({ title: "Stop event mode", sub: "Puts every setting back the way it was before the event.", ok: "Stop event", danger: true,
      body: `<p class="muted">Running since ${when(ev.started)}, started by ${esc(ev.by_name)}.</p>`,
      onOk: async () => { const r = await api("event", { server: key, action: "stop" }); toast("Event mode off. " + r.restored + " settings restored."); drawEventBanner(key); } });
  }
  modal({ title: "Event mode", sub: "For a match or tournament: sets a join password, turns bots, auto-balance and votes off, and keeps it that way until you stop it.", ok: "Start event",
    body: `<label>Password (empty makes one)</label><input name="password" maxlength="24" pattern="[A-Za-z0-9_-]{4,24}" placeholder="cup2026">
      <label>Note</label><input name="note" maxlength="120" placeholder="Clan cup semi-final">`,
    onOk: async (f) => { const r = await api("event", { server: key, action: "start", password: f.password, note: f.note }); toast("Event mode on. Password: " + r.password); drawEventBanner(key); } });
}

async function drawEventBanner(key) {
  const el = $("#event-banner");
  if (!el) return;
  try {
    const r = await api("event");
    S.events = Object.fromEntries(r.events.map((e) => [e.server, e]));
  } catch (e) { return; }
  const ev = S.events[key];
  el.innerHTML = ev ? `<div class="banner event"><span><b>Event mode</b>${ev.note ? " · " + esc(ev.note) : ""}${ev.password ? ` · password <span class="mono">${esc(ev.password)}</span>` : " · password set"} · since ${clock(ev.started)}, ${esc(ev.by_name)}</span>${can("event") ? '<button class="btn btn-small" id="ev-stop">Stop event</button>' : ""}</div>` : "";
  const stop = $("#ev-stop");
  if (stop) stop.onclick = () => eventDialog(key);
}

async function drawMap(key) {
  const box = $("#livemap");
  if (!box) return;
  let r;
  try { r = await api("positions?server=" + encodeURIComponent(key)); } catch (e) { box.innerHTML = `<p class="error">${esc(e.message)}</p>`; return; }
  if (!r.layout) { box.innerHTML = `<p class="empty">No layout image for ${esc(r.map || "this map")} yet.</p>`; return; }
  let wrap = box.querySelector(".livemap");
  if (!wrap || wrap.dataset.map !== r.map) {
    box.innerHTML = `<div class="livemap" data-map="${esc(r.map)}"><img src="${esc(r.layout.image)}" alt="${esc(r.map)} layout" width="${r.layout.w}" height="${r.layout.h}"></div>`;
    wrap = box.querySelector(".livemap");
    wrap.style.maxWidth = `calc(75vh * ${(r.layout.w / r.layout.h).toFixed(4)})`;   // tall maps stay on screen
  }
  for (const old of wrap.querySelectorAll(".pin")) old.remove();
  for (const pl of r.players) {
    if (pl.u == null || pl.u < 0 || pl.u > 1 || pl.v < 0 || pl.v > 1) continue;
    const pin = document.createElement("div");
    pin.className = `pin t${pl.team}${pl.alive ? "" : " dead"}${pl.bot ? " bot" : ""}`;
    pin.style.left = pl.u * 100 + "%";
    pin.style.top = pl.v * 100 + "%";
    pin.title = pl.name + (pl.alive ? " · " + pl.hp + " hp" : " · dead");
    const label = document.createElement("span");
    label.textContent = pl.name;
    pin.appendChild(label);
    wrap.appendChild(pin);
  }
}

async function showDemo(btn) {
  const out = $("#demo-" + btn.dataset.demo);
  try {
    const d = await api("demo?report=" + btn.dataset.demo);
    const m = Math.floor(d.offset_s / 60), sec = String(d.offset_s % 60).padStart(2, "0");
    out.innerHTML = `<a href="/api/demo/file?report=${esc(btn.dataset.demo)}" download>${esc(d.file)}</a> · ${(d.size / 1048576).toFixed(1)} MB · the report is at <b>${m}:${sec}</b> into the demo`;
  } catch (e) { out.textContent = e.message; }
}

function appealDialog(id, decision, name, done) {
  const accept = decision === "accept";
  modal({ title: (accept ? "Accept appeal from " : "Deny appeal from ") + name, ok: accept ? "Accept and lift the ban" : "Deny", danger: !accept,
    sub: "The player reads your answer when they check the appeal code. Write it for them, not for staff.",
    body: tplSelect("appeal", "answer") + `<label>Answer</label><textarea name="answer" maxlength="1000" required>${accept ? "" : ""}</textarea>`,
    onOk: async (f) => { await api("appeals/answer", { id, decision, answer: f.answer }); toast(accept ? "Appeal accepted, ban lifted." : "Appeal denied."); done(); refreshReportCount(); } });
}

function localInput(t) {
  const d = new Date(t * 1000);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function scheduleDialog(key) {
  const servers = S.servers.length ? S.servers : await loadServers();
  const acts = [["say", "Announce in chat", "server.say"], ["restart", "Restart the match", "schedule"], ["map", "Change map", "schedule"], ["nextmap", "Skip to the next map", "schedule"]].filter((a) => can(a[2]));
  modal({ title: "Schedule an action", sub: "Runs at the time you pick, once or on repeat. Times are in your own time zone.", ok: "Schedule",
    body: `<label>Server</label><select name="server">${can("server.say") ? '<option value="*">Every server (announcements only)</option>' : ""}${servers.map((x) => `<option value="${esc(x.key)}"${x.key === key ? " selected" : ""}>${esc(x.name)}</option>`).join("")}</select>
      <label>Action</label><select name="action">${acts.map((a) => `<option value="${a[0]}">${a[1]}</option>`).join("")}</select>
      ${tplSelect("chat", "text")}<label>Message (announcements)</label><input name="text" maxlength="200" placeholder="Clan cup starts in 10 minutes on Official #2">
      <label>Map (map changes)</label><select name="map"><option value="">Next in rotation</option>${(S.me.maps || []).map((m) => `<option>${esc(m)}</option>`).join("")}</select>
      <label>First run</label><input type="datetime-local" name="at" value="${localInput(Date.now() / 1000 + 600)}">
      <label>Repeat every (minutes, empty for once)</label><input name="every" inputmode="numeric" placeholder="60">
      <label>Repeat until (optional)</label><input type="datetime-local" name="until">`,
    onOk: async (f) => {
      const at = Math.floor(new Date(f.at).getTime() / 1000);
      const until = f.until ? Math.floor(new Date(f.until).getTime() / 1000) : 0;
      await api("schedule", { server: f.server, action: f.action, text: f.text, map: f.map, at, every_min: +f.every || 0, until });
      toast("Scheduled for " + when(at) + ".");
      if (S.page === "schedule") route();
    } });
}

/* ------------------------------------------------------------------ alerts */
function pageAlerts(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Live</p><h1>Alerts</h1><p class="muted" id="al-hook"></p></div></div>
    <div class="grid grid-2"><div class="panel" id="al-list"></div><div><div class="panel"><h3>Suspicion right now</h3><div id="al-sus"></div></div></div></div>`;
  async function draw() {
    const [a, sus] = await Promise.all([api("alerts"), api("suspicion")]).catch((e) => { toast(e.message, true); return [null, null]; });
    if (!a) return;
    if (a.alerts.length) localStorage.setItem("alerts-seen", String(a.alerts[0].id));
    $("#al-hook").textContent = a.webhook ? "Alerts also go to the staff channel in Discord." : "The Discord staff channel is not connected; alerts show here only.";
    $("#al-list").innerHTML = a.alerts.map((x) => `<div class="alert-item"><div class="when">${when(x.at)}<div><span class="tag${["server_down", "dodger", "suspicion"].includes(x.kind) ? " bad" : ""}">${esc(x.kind.replace("_", " "))}</span></div></div>
      <div><b>${x.pid ? `<a href="#/player/${esc(x.pid)}">${esc(x.title)}</a>` : esc(x.title)}</b><div class="text">${md(x.text)}</div></div></div>`).join("") || '<p class="empty">No alerts yet.</p>';
    $("#al-sus").innerHTML = sus.players.length ? `<table><tr><th>Player</th><th class="num">Score</th></tr>${sus.players.map((x) => `<tr><td class="pname"><a href="#/player/${esc(x.pid)}">${esc(x.name)}</a><div class="dim small">${esc(x.reasons.join(" · "))}</div></td><td class="num">${susTag(x.score) || x.score}</td></tr>`).join("")}</table>`
      : '<p class="empty">Nobody online stands out.</p>';
  }
  every(draw, 15000, "alerts", ["alert"]);
}

/* ------------------------------------------------------------------ watchlist */
function pageWatchlist(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Cases</p><h1>Watchlist</h1><p class="muted">Staff get an alert whenever one of these players joins a server. Add players from their page.</p></div></div>
    <div class="panel table-wrap" id="w-list"></div>`;
  $("#w-list").onclick = (e) => {
    const b = e.target.closest("button[data-pid]"); if (!b) return;
    api("watchlist", { pid: b.dataset.pid, remove: true }).then(() => { toast("Removed."); draw(); }).catch((err) => toast(err.message, true));
  };
  async function draw() {
    const r = await api("watchlist").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    $("#w-list").innerHTML = r.watchlist.length ? `<table><tr><th>Player</th><th>Why</th><th>Added</th><th>Now</th><th></th></tr>${r.watchlist.map((w) => `
      <tr><td class="pname"><a href="#/player/${esc(w.pid)}">${esc(w.name)}</a></td><td>${esc(w.reason)}</td><td>${esc(w.by_name)} · ${when(w.created)}</td>
      <td>${w.online ? `<a class="tag ok" href="#/server/${esc(w.online)}">Online on ${esc(w.online)}</a>` : '<span class="dim">offline</span>'}</td>
      <td>${can("watch") ? `<button class="btn btn-small" data-pid="${esc(w.pid)}">Remove</button>` : ""}</td></tr>`).join("")}</table>` : '<p class="empty">Nobody is on the watchlist.</p>';
  }
  every(draw, 20000, "watchlist");
}

/* ------------------------------------------------------------------ stats review */
function pageReview(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Cases</p><h1>Stats review</h1><p class="muted">Numbers no fair player reaches. They count on the leaderboard until you void them. Voiding rebuilds the leaderboard.</p></div></div>
    <div class="panel table-wrap" id="rv-list"></div>`;
  $("#rv-list").onclick = (e) => {
    const b = e.target.closest("button[data-act]"); if (!b) return;
    const row = draw.rows[+b.dataset.i];
    const act = b.dataset.act;
    const body = { action: act === "checked" ? "checked" : "void", kind: act === "player" ? "player" : "match", id: act === "player" ? row.pid : row.match_id, pid: row.pid, match_id: row.match_id, reason: row.reason };
    if (act === "checked") return api("review", body).then(() => { toast("Marked as checked."); draw(); }).catch((err) => toast(err.message, true));
    modal({ title: act === "player" ? "Void every stat of " + (row.name || row.pid) : "Void this match", danger: true, ok: "Void",
      sub: act === "player" ? "Removes the player from every leaderboard and resets their rating. It can be restored later." : "Removes the match from every player's numbers and ratings.",
      body: `<label>Reason (kept with the record)</label><input name="reason" maxlength="200" value="${esc(row.reason)}">`,
      onOk: async (f) => { await api("review", Object.assign(body, { reason: f.reason })); toast("Voided. The leaderboard is rebuilt."); draw(); } });
  };
  async function draw() {
    let r;
    try { r = await api("review"); } catch (e) { $("#rv-list").innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
    draw.rows = r.review;
    $("#rv-list").innerHTML = r.review.length ? `<table><tr><th>Player</th><th>Why</th><th>Match</th><th>When</th><th></th></tr>${r.review.map((x, i) => `
      <tr><td class="pname"><a href="#/player/${esc(x.pid)}">${esc(x.name || x.pid)}</a></td><td>${esc(x.reason)}</td><td class="mono">${esc(x.match_id || "–")}</td>
      <td>${esc(String(x.created || "").replace("T", " ").slice(0, 16))}${x.checked ? `<div class="dim small">checked: ${esc(x.checked)}</div>` : ""}</td>
      <td><div class="row-actions"><button class="btn btn-small" data-act="checked" data-i="${i}">Fine</button>${x.match_id ? `<button class="btn btn-small btn-danger" data-act="match" data-i="${i}">Void match</button>` : ""}<button class="btn btn-small btn-danger" data-act="player" data-i="${i}">Void player</button></div></td></tr>`).join("")}</table>` : '<p class="empty">Nothing to review.</p>';
  }
  draw();
}

/* ------------------------------------------------------------------ schedule */
function pageSchedule(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Setup</p><h1>Schedule</h1><p class="muted">Announcements, restarts and map changes at a set time, once or on repeat.</p></div>
    <div class="actions">${can("server.say") ? '<button class="btn btn-primary" id="sc-new">New</button>' : ""}</div></div>
    <div class="panel table-wrap" id="sc-list"></div><div class="panel table-wrap"><h3>Done and cancelled</h3><div id="sc-done"></div></div>`;
  const nb = $("#sc-new");
  if (nb) nb.onclick = () => scheduleDialog("");
  $("#sc-list").onclick = (e) => {
    const b = e.target.closest("button[data-cancel]"); if (!b) return;
    api("schedule/cancel", { id: +b.dataset.cancel }).then(() => { toast("Cancelled."); draw(); }).catch((err) => toast(err.message, true));
  };
  const label = { say: "Announce", restart: "Restart match", map: "Change map", nextmap: "Next map" };
  const row = (j, live) => `<tr><td>${esc(label[j.action] || j.action)}</td><td>${esc(j.server === "*" ? "every server" : j.server)}</td><td>${esc(j.arg || "")}</td>
    <td>${live ? when(j.next_at) : j.last_run ? when(j.last_run) : "–"}${j.every_min ? `<div class="dim small">every ${j.every_min} min${j.until ? " until " + when(j.until) : ""}</div>` : ""}</td>
    <td>${esc(j.by_name)}</td><td>${j.runs ? j.runs + "×" : ""}${j.last_result ? `<div class="dim small">${esc(j.last_result)}</div>` : ""}</td>
    <td>${live ? `<button class="btn btn-small" data-cancel="${j.id}">Cancel</button>` : ""}</td></tr>`;
  async function draw() {
    const r = await api("schedule").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    const head = "<tr><th>Action</th><th>Server</th><th>Detail</th><th>When</th><th>By</th><th>Runs</th><th></th></tr>";
    $("#sc-list").innerHTML = r.jobs.length ? `<table>${head}${r.jobs.map((j) => row(j, true)).join("")}</table>` : '<p class="empty">Nothing scheduled.</p>';
    $("#sc-done").innerHTML = r.done.length ? `<table>${head}${r.done.map((j) => row(j, false)).join("")}</table>` : '<p class="empty">Nothing yet.</p>';
  }
  every(draw, 20000, "schedule");
}

/* ------------------------------------------------------------------ chat filter */
function pageFilter(main) {
  const admin = can("filters.manage");
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Setup</p><h1>Chat filter</h1><p class="muted">Words and patterns the portal watches for in chat on every server. Each hit is flagged and alerted; the action runs at most once a minute per player. Warn and mute need the 0.36.0 server; older servers flag only.</p></div>
    <div class="actions">${admin ? '<button class="btn btn-primary" id="f-new">Add</button>' : ""}</div></div>
    <div class="grid grid-2"><div class="panel table-wrap" id="f-list"></div>
    <div><div class="panel"><h3>Try a message</h3><form id="f-test" class="inline-form"><input name="text" maxlength="300" placeholder="Type a chat line"><button class="btn">Test</button></form><p id="f-result" class="muted"></p></div>
    <div class="panel"><h3>Recently flagged</h3><div class="chat-log" id="f-flagged"></div></div></div></div>`;
  const edit = (f = {}) => modal({ title: f.id ? "Change filter" : "Add a filter", ok: "Save",
    sub: "Words match whole words, ignore case and common swaps such as 0 for o. End with * to catch endings: noob* also catches noobs.",
    body: `<label>Type</label><select name="kind"><option value="word"${f.kind === "regex" ? "" : " selected"}>Word or phrase</option><option value="regex"${f.kind === "regex" ? " selected" : ""}>Pattern (regular expression)</option></select>
      <label>Word or pattern</label><input name="pattern" maxlength="200" value="${esc(f.pattern || "")}" required>
      <label>Then</label><select name="action">${[["flag", "Flag and alert only"], ["warn", "Warn the player"], ["mute", "Mute the player"], ["kick", "Kick the player"]].map(([v, l]) => `<option value="${v}"${f.action === v ? " selected" : ""}>${l}</option>`).join("")}</select>
      <label>Mute length</label><select name="length">${["10m", "30m", "1h", "12h"].map((l) => `<option${f.minutes && f.minutes + "m" === l ? " selected" : ""}>${l}</option>`).join("")}</select>
      <label>Label the player sees as the reason</label><input name="note" maxlength="60" value="${esc(f.note || "")}" placeholder="Insult">
      <label class="check"><input type="checkbox" name="active"${f.active === 0 ? "" : " checked"}> Active</label>`,
    onOk: async (v) => { await api("filters", Object.assign({ id: f.id }, v)); toast("Saved."); draw(); } });
  const nb = $("#f-new");
  if (nb) nb.onclick = () => edit();
  $("#f-list").onclick = (e) => {
    const b = e.target.closest("button[data-i]"); if (!b) return;
    const f = draw.rows[+b.dataset.i];
    if (b.dataset.do === "delete") return api("filters/delete", { id: f.id }).then(() => { toast("Deleted."); draw(); }).catch((err) => toast(err.message, true));
    edit(f);
  };
  $("#f-test").onsubmit = async (e) => {
    e.preventDefault();
    const r = await api("filters/test", { text: e.target.text.value }).catch((err) => { toast(err.message, true); return null; });
    if (r) $("#f-result").textContent = r.matches.length ? "Matches: " + r.matches.map((m) => `${m.pattern} (${m.action})`).join(", ") : "No filter matches.";
  };
  async function draw() {
    const r = await api("filters").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    draw.rows = r.filters;
    $("#f-list").innerHTML = r.filters.length ? `<table><tr><th>Filter</th><th>Then</th><th class="num">Hits</th><th></th></tr>${r.filters.map((f, i) => `
      <tr><td><span class="mono">${esc(f.pattern)}</span> ${f.kind === "regex" ? '<span class="tag">pattern</span>' : ""}${f.active ? "" : ' <span class="tag">off</span>'}<div class="dim small">${esc(f.note || "")}</div></td>
      <td>${esc(f.action)}${f.action === "mute" ? " " + f.minutes + " min" : ""}</td><td class="num">${f.hits}</td>
      <td>${admin ? `<div class="row-actions"><button class="btn btn-small" data-i="${i}">Change</button><button class="btn btn-small btn-danger" data-i="${i}" data-do="delete">Delete</button></div>` : ""}</td></tr>`).join("")}</table>` : '<p class="empty">No filters yet.</p>';
    $("#f-flagged").innerHTML = r.flagged.map((l) => `<div class="chat-line flagged"><time>${when(l.at)}</time><span class="srv">${esc(l.server)}</span>${l.pid ? `<a class="who" href="#/player/${esc(l.pid)}">${esc(l.name)}:</a>` : `<span class="who">${esc(l.name)}:</span>`} ${esc(l.text)}<span class="flag">${esc(l.flag)}</span></div>`).join("") || '<p class="empty">Nothing flagged.</p>';
  }
  draw();
}

/* ------------------------------------------------------------------ saved replies */
function pageReplies(main) {
  const admin = can("templates.manage");
  const kinds = { warn: "Warnings", kick: "Kick reasons", mute: "Mute reasons", ban: "Ban reasons", chat: "Chat and announcements", appeal: "Appeal answers", close: "Closing a report" };
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Setup</p><h1>Saved replies</h1><p class="muted">Ready-made texts in the warn, kick, mute, ban, chat, appeal and report dialogs. One wording for the whole team.</p></div>
    <div class="actions">${admin ? '<button class="btn btn-primary" id="t-new">Add</button>' : ""}</div></div><div id="t-list"></div>`;
  const edit = (t = {}) => modal({ title: t.id ? "Change saved reply" : "Add a saved reply", ok: "Save",
    body: `<label>Used for</label><select name="kind">${Object.entries(kinds).map(([k, l]) => `<option value="${k}"${t.kind === k ? " selected" : ""}>${l}</option>`).join("")}</select>
      <label>Name</label><input name="title" maxlength="40" value="${esc(t.title || "")}" required><label>Text</label><textarea name="text" maxlength="500" required>${esc(t.text || "")}</textarea>`,
    onOk: async (f) => { await api("templates", Object.assign({ id: t.id }, f)); S.templates = null; toast("Saved."); draw(); } });
  const nb = $("#t-new");
  if (nb) nb.onclick = () => edit();
  $("#t-list").onclick = (e) => {
    const b = e.target.closest("button[data-id]"); if (!b) return;
    const t = S.templates.find((x) => x.id === +b.dataset.id);
    if (b.dataset.do === "delete") return api("templates", { id: t.id, delete: true }).then(() => { S.templates = null; draw(); }).catch((err) => toast(err.message, true));
    edit(t);
  };
  async function draw() {
    S.templates = null;
    const list = await templates();
    $("#t-list").innerHTML = Object.entries(kinds).map(([k, label]) => {
      const rows = list.filter((t) => t.kind === k);
      return `<div class="panel"><h3>${label}</h3><ul class="list">${rows.map((t) => `<li><div class="head"><div><b>${esc(t.title)}</b><div class="muted">${esc(t.text)}</div></div>
        ${admin ? `<div class="actions"><button class="btn btn-small" data-id="${t.id}">Change</button><button class="btn btn-small btn-danger" data-id="${t.id}" data-do="delete">Delete</button></div>` : ""}</div></li>`).join("") || '<li class="dim">None yet.</li>'}</ul></div>`;
    }).join("");
  }
  draw();
}

/* ------------------------------------------------------------------ weekly report */
function pageWeekly(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Setup</p><h1>Weekly report</h1><p class="muted">Posted to the staff channel every Monday at 08:00 Belgian time.</p></div>
    <div class="tabs" id="wk-tabs"><button class="btn btn-small on" data-w="0">Last 7 days</button><button class="btn btn-small" data-w="1">The week before</button><button class="btn btn-small" data-w="2">Two weeks back</button></div></div>
    <div id="wk"></div>`;
  $("#wk-tabs").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#wk-tabs").children) x.classList.toggle("on", x === b); draw(+b.dataset.w); };
  async function draw(weeks = 0) {
    const w = await api("weekly?weeks_ago=" + weeks).catch((e) => { toast(e.message, true); return null; });
    if (!w) return;
    const tile = (label, value, note = "") => `<div class="card"><div class="meta">${label}</div><div class="stat">${value}</div><div class="dim small">${note}</div></div>`;
    const a = w.actions;
    $("#wk").innerHTML = `<div class="tiles">${[
      tile("Players", w.players, w.new_players + " new"),
      tile("Peak online", Math.max(0, ...Object.values(w.peaks)), Object.entries(w.peaks).map(([k, v]) => k + " " + v).join(" · ")),
      tile("Bans", a.ban, w.bans_by_moderators + " by moderators · " + a.unban + " lifted"),
      tile("Kicks, mutes, warnings", a.kick + a.mute + a.warn, `${a.kick} · ${a.mute} · ${a.warn}`),
      tile("Automatic actions", w.auto_actions, "chat filter, AFK and team-kill watch"),
      tile("Reports in", Object.values(w.reports_in).reduce((x, y) => x + y, 0), Object.entries(w.reports_in).map(([k, v]) => k + " " + v).join(" · ")),
      tile("Reports closed", w.reports_closed, w.median_close_minutes != null ? "median " + w.median_close_minutes + " min" : ""),
      tile("Open now", w.open_now),
    ].join("")}</div>
    <div class="grid grid-2"><div class="panel"><h3>Staff activity</h3>${w.staff.length ? `<table><tr><th>Staff</th><th class="num">Actions</th></tr>${w.staff.map((x) => `<tr><td>${esc(x.staff)} <span class="role">${esc(x.role)}</span></td><td class="num">${x.n}</td></tr>`).join("")}</table>` : '<p class="empty">No staff actions.</p>'}</div>
    <div class="panel"><h3>As posted in Discord</h3><div class="text-block small">${md(w.text)}</div></div></div>`;
  }
  draw();
}

/* ------------------------------------------------------------------ website insights */
function pageInsights(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Community</p><h1>Insights</h1><p class="muted">Website visits, the channels that bring them and the downloads they lead to. Daily totals only: no cookies, no IP addresses, nothing per person. Visitors are counted once per day, so a week's visitors add up daily counts.</p></div>
    <div class="tabs" id="in-tabs"><button class="btn btn-small" data-d="7">7 days</button><button class="btn btn-small on" data-d="30">30 days</button><button class="btn btn-small" data-d="90">90 days</button><button class="btn btn-small" data-d="365">Year</button></div></div>
    <div id="in"></div>`;
  $("#in-tabs").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#in-tabs").children) x.classList.toggle("on", x === b); draw(+b.dataset.d); };
  const n = (v) => Number(v || 0).toLocaleString("en-GB");
  const pct = (a, b) => (b ? (100 * a / b).toFixed(1) + "%" : "–");
  function chart(days, visitors, downloads, la = "visitors", lb = "downloads", aria = "Visitors and downloads per day") {
    const W = 760, H = 150, max = Math.max(1, ...visitors), bw = W / days.length;
    const bars = visitors.map((v, i) => {
      const h = Math.round((H - 18) * v / max), d = Math.round((H - 18) * (downloads[i] || 0) / max);
      return `<g><title>${esc(days[i])}: ${v} ${la}, ${downloads[i] || 0} ${lb}</title>
        <rect class="in-v" x="${(i * bw + 1).toFixed(1)}" y="${H - 14 - h}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h}"></rect>
        <rect class="in-d" x="${(i * bw + 1).toFixed(1)}" y="${H - 14 - d}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${d}"></rect></g>`;
    }).join("");
    return `<svg class="in-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${aria}">${bars}
      <text class="in-axis" x="0" y="${H - 2}">${esc(days[0])}</text><text class="in-axis" x="${W}" y="${H - 2}" text-anchor="end">${esc(days[days.length - 1])}</text>
      <text class="in-axis" x="0" y="10">${max}</text></svg>
      <p class="dim small"><span class="in-key in-v"></span> ${la} <span class="in-key in-d"></span> ${lb}</p>`;
  }
  function table(rows, cols, empty) {
    if (!rows || !rows.length) return `<p class="empty">${empty}</p>`;
    return `<table><tr>${cols.map((c) => `<th${c.num ? ' class="num"' : ""}>${c.label}</th>`).join("")}</tr>${rows.map((r) =>
      `<tr>${cols.map((c) => `<td${c.num ? ' class="num"' : ""}>${c.fmt ? c.fmt(r) : esc(r[c.key])}</td>`).join("")}</tr>`).join("")}</table>`;
  }
  async function draw(days = 30) {
    let r;
    try { r = await api("insights?days=" + days); } catch (e) { $("#in").innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
    const t = r.totals, gh = r.github || { releases: [], daily: [] };
    const ghTotal = gh.releases.reduce((a, x) => a + x.downloads, 0), ghPeriod = (gh.daily || []).reduce((a, x) => a + x, 0);
    const tile = (label, value, note = "") => `<div class="card"><div class="meta">${label}</div><div class="stat">${value}</div><div class="dim small">${note}</div></div>`;
    const name = { key: "name", label: "Name" };
    const vis = { label: "Visitors", num: true, fmt: (x) => n(x.visitors) };
    const views = { label: "Views", num: true, fmt: (x) => n(x.views) };
    const dls = { label: "Downloads", num: true, fmt: (x) => n(x.downloads) };
    const conv = { label: "Download rate", num: true, fmt: (x) => pct(x.downloads, x.visitors) };
    $("#in").innerHTML = `<div class="tiles">${[
      tile("Visitors", n(t.visitors), "daily unique, added up"),
      tile("Page views", n(t.views), t.visitors ? (t.views / t.visitors).toFixed(1) + " per visitor" : ""),
      tile("Download clicks", n(t.downloads), pct(t.downloads, t.visitors) + " of visitors"),
      tile("GitHub downloads", n(ghPeriod), n(ghTotal) + " all time, every release"),
    ].join("")}</div>
    <div class="panel"><h3>Per day</h3>${chart(r.days, r.series.visitors, r.series.downloads)}</div>
    <div class="grid grid-2">
      <div class="panel table-wrap"><h3>Channels</h3><p class="dim small">From the campaign tag of a truecombat.eu/go link, else the referring site, else direct.</p>${table(r.sources, [name, vis, views, dls, conv], "No visits yet.")}</div>
      <div class="panel table-wrap"><h3>Campaigns</h3><p class="dim small">source / medium / campaign / content</p>${table(r.campaigns, [name, vis, dls, conv], "No campaign links used yet.")}</div>
      <div class="panel table-wrap"><h3>Pages</h3>${table(r.pages, [name, views, vis, dls], "No page views yet.")}</div>
      <div class="panel table-wrap"><h3>Referring sites</h3>${table(r.referrers, [name, vis], "No referring sites yet.")}</div>
      <div class="panel table-wrap"><h3>Countries</h3>${table(r.countries, [name, vis], "No visits yet.")}</div>
      <div class="panel table-wrap"><h3>Screens and languages</h3>${table(r.devices, [name, vis], "No visits yet.")}${table(r.langs, [{ key: "name", label: "Language" }, vis], "")}</div>
      <div class="panel table-wrap"><h3>GitHub release downloads</h3><p class="dim small">Public counts read every six hours; includes launcher and updater downloads of the installer.</p>${table(gh.releases.slice(0, 12), [{ key: "tag", label: "Release" }, { label: "Downloads", num: true, fmt: (x) => n(x.downloads) }], "Not read yet.")}</div>
    </div>
    ${launcher(r.launcher, r.days)}
    <p class="dim small">Updated ${esc(r.updated)}. Country lookup: IP to Country Lite by DB-IP (CC BY 4.0).</p>`;
  }
  /* launcher 2.6.0+: anonymous crash and hardware reports from players who chose to share */
  function launcher(l, days) {
    if (!l) return "";
    const t = l.totals, tile = (label, value, note = "") => `<div class="card"><div class="meta">${label}</div><div class="stat">${value}</div><div class="dim small">${note}</div></div>`;
    const rate = (c, s) => (s ? (100 * c / s).toFixed(2) + "%" : "–");
    const hw = l.hardware || {}, cnt = { label: "Launchers", num: true, fmt: (x) => n(x.count) };
    const share = (rows) => { const all = (rows || []).reduce((a, x) => a + x.count, 0); return { label: "Share", num: true, fmt: (x) => pct(x.count, all) }; };
    const hwTable = (title, dim, label) => `<div class="panel table-wrap"><h3>${title}</h3>${table(hw[dim], [{ key: "name", label }, cnt, share(hw[dim])], "No hardware reports yet.")}</div>`;
    const crashCols = [
      { label: "Crash", fmt: (x) => `<span class="mono">${esc(x.at)}</span><div class="dim small">${esc(x.program)} · ${esc(x.code)} ${esc(x.kind)}</div>${x.frames.length ? `<details class="small"><summary>Stack</summary><div class="mono">${x.frames.map(esc).join("<br>")}</div></details>` : ""}` },
      { label: "Count", num: true, fmt: (x) => n(x.count) },
      { label: "Versions", fmt: (x) => Object.entries(x.games).sort((a, b) => b[1] - a[1]).map(([g, c]) => `${esc(g)} <span class="dim">(${c})</span>`).join("<br>") },
      { label: "Graphics", fmt: (x) => Object.entries(x.gpuvendors).sort((a, b) => b[1] - a[1]).map(([g, c]) => `${esc(g)} <span class="dim">(${c})</span>`).join("<br>") || '<span class="dim">–</span>' },
      { label: "Minutes in", num: true, fmt: (x) => esc(x.avg_minutes) },
      { label: "Seen", fmt: (x) => `${esc(x.first_seen)}<div class="dim small">last ${esc(x.last_seen)}</div>` },
    ];
    return `<div class="head in-section"><div><p class="eyebrow">Launcher</p><h2>Crashes and hardware</h2><p class="muted">From players who chose "Share" in the launcher (2.6.0 and later). Anonymous: no IDs, nothing ties one report to the next. Starts and crashes are daily counts per game version; hardware is counted once per launcher per month.</p></div></div>
    <div class="tiles">${[
      tile("Game starts", n(t.launches), n(t.safe) + " Safe starts (OpenGL)"),
      tile("Crashes", n(t.crashes), rate(t.crashes, t.launches) + " of starts"),
      tile("Reports", n(t.reports), "one per launcher per day at most"),
      tile("Launchers this month", n(l.hardware_reports), l.hardware_month ? "hardware reports in " + esc(l.hardware_month) : "none yet"),
    ].join("")}</div>
    <div class="panel"><h3>Per day</h3>${chart(days, l.series.launches, l.series.crashes, "game starts", "crashes", "Game starts and crashes per day")}</div>
    <div class="panel table-wrap"><h3>Versions</h3>${table(l.versions, [{ key: "game", label: "Game version" }, { label: "Starts", num: true, fmt: (x) => n(x.launches) }, { label: "Crashes", num: true, fmt: (x) => n(x.crashes) }, { label: "Crash rate", num: true, fmt: (x) => rate(x.crashes, x.launches) }, { label: "Safe starts", num: true, fmt: (x) => pct(x.safe, x.launches) }], "No reports yet.")}</div>
    <div class="panel table-wrap"><h3>Top crashes</h3><p class="dim small">Grouped by program, exception and code location (module+offset). Match offsets against the symbols kept with each build (RUN/symbols).</p>${table(l.crashes, crashCols, "No crashes reported. Good.")}</div>
    <div class="grid grid-2">
      ${hwTable("Graphics cards", "gpu", "Card")}${hwTable("Processors", "cpu", "Processor")}
      ${hwTable("Windows", "os", "Version")}${hwTable("Memory", "ram", "RAM")}
      ${hwTable("Video memory", "vram", "VRAM")}${hwTable("Desktop resolution", "display", "Resolution")}
      ${hwTable("Refresh rate", "refresh", "Rate")}${hwTable("DirectX 12", "dx12", "Works")}
      ${hwTable("Graphics vendor", "gpuvendor", "Vendor")}${hwTable("Countries", "country", "Country")}
      ${hwTable("Launcher versions", "launcher", "Launcher")}${hwTable("Launcher language", "lang", "Language")}
    </div>`;
  }
  draw();
}

/* ------------------------------------------------------------------ settings (config editor) */
function cvarShown(c) {
  if (c.value == null) return null;
  if (c.shown) return c.shown;
  if (c.type === "bool") return c.value === "1" ? "On" : c.value === "0" ? "Off" : c.value;
  if (c.type === "choice") { const h = (c.choices || []).find((x) => x[0] === c.value); return h ? h[1] : c.value; }
  if (c.type === "words" && c.value === "") return "none";
  return c.value === "" ? "(empty)" : c.value;
}
function cvarInput(c) {
  const cur = c.kept ?? c.value ?? "";
  if (c.type === "bool" || c.type === "choice") {
    const opts = c.type === "bool" ? [["0", "Off"], ["1", "On"]] : c.choices;
    return `<label>New value</label><select name="value">${opts.map(([v, l]) => `<option value="${esc(v)}"${v === cur ? " selected" : ""}>${esc(l)} (${esc(v)})</option>`).join("")}</select>`;
  }
  if (c.type === "int") {
    return `<label>New value${c.min != null ? ` <span class="dim">(${c.min} to ${c.max})</span>` : ""}</label><input name="value" type="number" step="1"${c.min != null ? ` min="${c.min}" max="${c.max}"` : ""} value="${esc(cur)}" required>`;
  }
  if (c.type === "words") {
    const on = new Set(String(cur).toLowerCase().split(/[\s,]+/).filter(Boolean));
    return `<label>Pick the words</label><div class="cv-words">${c.words.map((w) => `<label class="check"><input type="checkbox" data-word="${esc(w)}"${on.has(w) ? " checked" : ""}> ${esc(w)}</label>`).join("")}</div>
      <input type="hidden" name="value" value="${esc(cur)}">`;
  }
  const hint = c.type === "weather" ? ' placeholder="random, clear, rain, storm:80 …"' : "";
  return `<label>New value</label><input name="value" maxlength="64" value="${esc(cur)}"${hint}>`;
}
async function pageSettings(main, key) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow"><a href="#/server/${esc(key)}">Server</a></p><h1>Settings</h1><p class="muted">Live server settings. "Keep" makes the portal put the value back after a restart or a config reload; without it the change lasts until the server restarts. Settings marked "next map" are read when the next map loads.</p></div></div>
    <div class="grid grid-2"><div class="panel table-wrap"><input id="cv-filter" class="cv-filter" type="search" placeholder="Find a setting" aria-label="Find a setting"><div id="cv-list"></div></div><div class="panel"><h3>History</h3><div id="cv-hist"></div></div></div>`;
  $("#cv-filter").oninput = () => paint();
  $("#cv-list").onclick = (e) => {
    const b = e.target.closest("button[data-i]"); if (!b) return;
    const c = draw.rows[+b.dataset.i];
    if (b.dataset.do === "release") return api("cvars/release", { server: key, cvar: c.name }).then(() => { toast("No longer kept."); draw(); }).catch((err) => toast(err.message, true));
    modal({ title: c.label, sub: c.name + " · now " + (cvarShown(c) ?? "unknown"), ok: "Apply",
      body: `${c.help ? `<p class="dim small">${esc(c.help)}</p>` : ""}${cvarInput(c)}
        <label class="check"><input type="checkbox" name="keep"${c.kept != null ? " checked" : ""}> Keep after restarts</label>`,
      onOk: async (f) => { const r = await api("cvars", { server: key, cvar: c.name, value: f.value, keep: f.keep }); toast(r.note || c.name + " is now " + r.value + "."); draw(); } });
    const words = $("#modal-body .cv-words");
    if (words) words.onchange = () => { $('#modal-body input[name="value"]').value = [...words.querySelectorAll("input[data-word]:checked")].map((x) => x.dataset.word).join(" "); };
  };
  $("#cv-hist").onclick = (e) => {
    const b = e.target.closest("button[data-rb]"); if (!b) return;
    api("cvars/rollback", { id: +b.dataset.rb }).then((r) => { toast("Rolled back to " + r.value + "."); draw(); }).catch((err) => toast(err.message, true));
  };
  function paint() {
    const r = draw.data; if (!r) return;
    const q = ($("#cv-filter").value || "").trim().toLowerCase();
    const groups = [...(r.groups || []), "Other"].filter((g, i, a) => a.indexOf(g) === i);
    const row = (c, i) => `
      <tr><td>${esc(c.label)}${c.next_map ? ' <span class="tag" title="Read when the next map loads">next map</span>' : ""}${c.view ? ' <span class="tag" title="Shown for reference, not changed from the portal">view only</span>' : ""}<div class="cvar-name">${esc(c.name)}</div>${c.help ? `<div class="dim small cv-help">${esc(c.help)}</div>` : ""}</td>
      <td class="mono">${c.value == null ? `<span class="dim">${r.offline ? "server not answering" : "not on this server"}</span>` : esc(cvarShown(c))}${c.kept != null ? ' <span class="kept" title="Kept after restarts">kept</span>' : ""}${c.event ? ' <span class="tag">event</span>' : ""}</td>
      <td><div class="row-actions">${c.value != null && !c.event && !c.view ? `<button class="btn btn-small" data-i="${i}">Change</button>` : ""}${c.kept != null ? `<button class="btn btn-small" data-i="${i}" data-do="release">Stop keeping</button>` : ""}</div></td></tr>`;
    const hit = (c) => !q || (c.label + " " + c.name + " " + (c.help || "") + " " + (c.group || "")).toLowerCase().includes(q);
    const html = groups.map((g) => {
      const items = r.cvars.map((c, i) => [c, i]).filter(([c]) => (c.group || "Other") === g && hit(c));
      return items.length ? `<h3 class="cv-group">${esc(g)}</h3><table><tr><th>Setting</th><th>Value</th><th></th></tr>${items.map(([c, i]) => row(c, i)).join("")}</table>` : "";
    }).join("");
    $("#cv-list").innerHTML = html || '<p class="empty">No setting matches.</p>';
  }
  async function draw() {
    let r;
    try { r = await api("cvars?server=" + encodeURIComponent(key)); } catch (e) { $("#cv-list").innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
    draw.rows = r.cvars; draw.data = r;
    paint();
    $("#cv-hist").innerHTML = r.history.length ? `<ul class="list">${r.history.map((h) => `<li><span class="mono">${esc(h.cvar)}</span> ${esc(h.old)} → <b>${esc(h.new)}</b>
      <div class="dim small">${esc(h.kind)}${h.kept ? ", kept" : ""} · ${esc(h.by_name)} · ${when(h.at)}</div>
      ${["set", "rollback"].includes(h.kind) ? `<button class="btn btn-small" data-rb="${h.id}">Roll back to ${h.old === "" ? "(empty)" : esc(h.old)}</button>` : ""}</li>`).join("")}</ul>` : '<p class="empty">No changes yet.</p>';
  }
  $("#cv-list").innerHTML = '<p class="empty">Reading the server settings…</p>';
  draw();
}


/* ------------------------------------------------------------------ 1.4: navigation, search and shortcuts */
const NAV_KEY = "nav-closed";
function navSetup() {
  let closed = [];
  try { closed = JSON.parse(localStorage.getItem(NAV_KEY) || "[]"); } catch (e) { closed = []; }
  for (const g of document.querySelectorAll("#nav .nav-group")) {
    g.classList.toggle("closed", closed.includes(g.dataset.group));
    g.querySelector(".nav-head").onclick = () => {
      g.classList.toggle("closed");
      const now = [...document.querySelectorAll("#nav .nav-group.closed")].map((x) => x.dataset.group);
      try { localStorage.setItem(NAV_KEY, JSON.stringify(now)); } catch (e) { /* private window */ }
    };
  }
  for (const a of document.querySelectorAll("#nav a[data-key]")) a.insertAdjacentHTML("beforeend", `<kbd class="key">g ${esc(a.dataset.key)}</kbd>`);
  $("#nav-toggle").onclick = () => ($("#side").classList.contains("open") ? closeNav() : openNav());
  $("#scrim").onclick = closeNav;
  $("#search-open").onclick = openPalette;
  $("#search-top").onclick = openPalette;
}
function openNav() { $("#side").classList.add("open"); $("#scrim").hidden = false; $("#nav-toggle").setAttribute("aria-expanded", "true"); }
function closeNav() { const s = $("#side"); if (!s) return; s.classList.remove("open"); $("#scrim").hidden = true; $("#nav-toggle").setAttribute("aria-expanded", "false"); }

function typing(e) {
  const t = e.target;
  return t && (t.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(t.tagName));
}
function shortcutKey(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); return $("#palette").hidden ? openPalette() : closePalette(); }
  if (typing(e) || e.ctrlKey || e.metaKey || e.altKey || !$("#modal").hidden || !$("#palette").hidden) return;
  if (e.key === "/") { e.preventDefault(); return openPalette(); }
  if (e.key === "?") { e.preventDefault(); return shortcutHelp(); }
  if (e.key === "g") { shortcutKey.g = Date.now(); return; }
  if (shortcutKey.g && Date.now() - shortcutKey.g < 1200) {
    shortcutKey.g = 0;
    const a = document.querySelector(`#nav a[data-key="${CSS.escape(e.key)}"]`);
    if (a && !a.hidden) { e.preventDefault(); location.hash = a.getAttribute("href"); }
  }
}
function shortcutHelp() {
  const keys = [...document.querySelectorAll("#nav a[data-key]")].filter((a) => !a.hidden)
    .map((a) => `<dt><kbd>g</kbd> <kbd>${esc(a.dataset.key)}</kbd></dt><dd>${esc(a.firstChild.textContent.trim())}</dd>`).join("");
  modal({ title: "Keyboard shortcuts", ok: "Close", onOk: () => {},
    body: `<dl class="shortcuts"><dt><kbd>Ctrl</kbd> <kbd>K</kbd> or <kbd>/</kbd></dt><dd>Search players, bans, reports and pages, or run a command</dd>
      <dt><kbd>?</kbd></dt><dd>This list</dd><dt><kbd>Esc</kbd></dt><dd>Close a dialog</dd>${keys}</dl>
      <p class="dim small">Commands in search: <span class="mono">warn</span>, <span class="mono">mute</span>, <span class="mono">kick</span>, <span class="mono">ban</span>, <span class="mono">punish</span> or <span class="mono">move</span> followed by part of a name opens that dialog for a player who is online. <span class="mono">announce</span> messages every server.</p>` });
}

const VERBS = { warn: ["player.warn", "Warn"], mute: ["player.mute", "Mute"], kick: ["player.kick", "Kick"], ban: ["ban.temp", "Ban"],
  punish: ["punish", "Punish"], move: ["player.move", "Move"] };
const P = { items: [], on: 0, seq: 0, timer: 0 };
function paletteSetup() {
  const input = $("#palette-q");
  input.oninput = () => { clearTimeout(P.timer); P.timer = setTimeout(paletteSearch, 140); paletteDraw(paletteLocal(input.value), true); };
  input.onkeydown = (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); P.on = Math.max(0, Math.min(P.items.length - 1, P.on + (e.key === "ArrowDown" ? 1 : -1))); paletteMark(); }
    else if (e.key === "Enter") { e.preventDefault(); paletteRun(P.items[P.on]); }
    else if (e.key === "Escape") { e.preventDefault(); closePalette(); }
  };
  $("#palette").onclick = (e) => { if (e.target.id === "palette") closePalette(); };
  $("#palette-list").onclick = (e) => { const it = e.target.closest(".palette-item"); if (it) { e.preventDefault(); paletteRun(P.items[+it.dataset.i]); } };
  $("#palette-list").onmousemove = (e) => { const it = e.target.closest(".palette-item"); if (it && +it.dataset.i !== P.on) { P.on = +it.dataset.i; paletteMark(); } };
}
function openPalette() {
  closeNav();
  $("#palette").hidden = false;
  const input = $("#palette-q");
  input.value = "";
  paletteDraw(paletteLocal(""), false);
  input.focus();
  loadServers().then(() => { if (!$("#palette").hidden) paletteDraw(paletteLocal(input.value), true); }).catch(() => {});
}
function closePalette() { const p = $("#palette"); if (p) p.hidden = true; }
function pageEntries() {
  return [...document.querySelectorAll("#nav a")].filter((a) => !a.hidden && !(a.closest(".nav-group") || {}).hidden)
    .map((a) => ({ kind: "Page", label: a.firstChild.textContent.trim(), href: a.getAttribute("href"), sub: a.closest(".nav-group") ? a.closest(".nav-group").querySelector(".nav-head").textContent : "" }));
}
function paletteLocal(q) {
  const low = q.trim().toLowerCase();
  const out = [];
  const verb = low.split(/\s+/)[0];
  if (VERBS[verb] && can(VERBS[verb][0])) {
    const who = low.slice(verb.length).trim();
    for (const s of S.servers) for (const p of s.players || []) {
      if (p.bot || (who && !p.name.toLowerCase().includes(who))) continue;
      if (verb === "punish" && !p.pid) continue;
      out.push({ kind: VERBS[verb][1], label: `${VERBS[verb][1]} ${p.name}`, sub: s.name, act: () => playerAction(s.key, p.slot, p.name, verb, p.pid) });
    }
    if (!out.length) out.push({ kind: "Hint", label: who ? `Nobody online matches "${who}"` : "Type part of a player's name", sub: "", act: null });
    return out.slice(0, 12);
  }
  if ("announce".startsWith(verb) && verb.length >= 3 && can("server.say")) out.push({ kind: "Command", label: "Message every server", sub: "announce", act: () => sayDialog("*") });
  if (/^(sched)/.test(verb) && can("server.say")) out.push({ kind: "Command", label: "Schedule an action", sub: "", act: () => scheduleDialog("") });
  if (/^(case|new c)/.test(low) && can("cases")) out.push({ kind: "Command", label: "Open a new case", sub: "", act: () => newCaseDialog({}) });
  if (/^(short|keys|help)/.test(verb)) out.push({ kind: "Command", label: "Keyboard shortcuts", sub: "?", act: shortcutHelp });
  for (const e of pageEntries()) if (!low || e.label.toLowerCase().includes(low) || e.sub.toLowerCase().includes(low)) out.push(e);
  for (const s of S.servers) if (!low || s.name.toLowerCase().includes(low) || s.key.includes(low)) out.push({ kind: "Server", label: s.name, sub: s.online ? `${s.map} · ${s.humans} players` : "offline", href: "#/server/" + s.key });
  return low ? out.slice(0, 10) : out.slice(0, 14);
}
async function paletteSearch() {
  const q = $("#palette-q").value.trim();
  const local = paletteLocal(q);
  if (q.length < 2 || VERBS[q.toLowerCase().split(/\s+/)[0]]) return paletteDraw(local, false);
  const seq = ++P.seq;
  let r;
  try { r = await api("search?q=" + encodeURIComponent(q)); } catch (e) { return paletteDraw(local, false); }
  if (seq !== P.seq || $("#palette").hidden) return;
  const found = [];
  for (const o of r.online) found.push({ kind: "Online", label: o.name, sub: o.server_name, href: o.pid ? "#/player/" + o.pid : "#/server/" + o.server });
  for (const p of r.players) if (!r.online.some((o) => o.pid === p.pid)) found.push({ kind: "Player", label: p.names[0] || p.pid, sub: (p.banned ? "banned · " : "") + (p.last_seen ? "seen " + ago(p.last_seen) : "stats only"), href: "#/player/" + p.pid });
  for (const b of r.bans) found.push({ kind: "Ban", label: `#${b.id} ${b.name}`, sub: (b.active ? until(b.expires) : "lifted") + " · " + b.reason, href: b.pid ? "#/player/" + b.pid : "#/bans" });
  for (const x of r.reports) found.push({ kind: x.source === "bug" ? "Bug" : x.source === "appeal" ? "Appeal" : "Report", label: `#${x.id} ${x.target_name || x.summary}`, sub: x.status + " · " + x.summary, href: "#/reports" });
  for (const c of r.cases || []) found.push({ kind: "Case", label: `#${c.id} ${c.title}`, sub: c.status + (c.assignee ? " · " + c.assignee : ""), href: "#/case/" + c.id });
  for (const x of r.staff) found.push({ kind: "Staff", label: x.name || x.discord_id, sub: x.role || "Discord role", href: "#/staff" });
  paletteDraw(found.concat(local), false);
}
function paletteDraw(items, keepOn) {
  P.items = items;
  if (!keepOn || P.on >= items.length) P.on = 0;
  let last = "";
  $("#palette-list").innerHTML = items.map((it, i) => {
    const group = it.kind === "Page" ? "Pages" : it.kind === "Server" ? "Servers" : ["Command", "Hint"].includes(it.kind) || VERBS[it.label.split(" ")[0].toLowerCase()] ? "Actions" : "Results";
    const head = group !== last ? `<div class="palette-sec">${group}</div>` : "";
    last = group;
    return `${head}<a class="palette-item" data-i="${i}" role="option"${it.href ? ` href="${esc(it.href)}"` : ""}><span class="kind">${esc(it.kind)}</span><span>${esc(it.label)}</span><span class="sub">${esc(it.sub || "")}</span></a>`;
  }).join("") || '<p class="empty">Nothing found.</p>';
  paletteMark();
}
function paletteMark() {
  for (const el of document.querySelectorAll("#palette-list .palette-item")) el.classList.toggle("on", +el.dataset.i === P.on);
  const on = document.querySelector("#palette-list .palette-item.on");
  if (on) on.scrollIntoView({ block: "nearest" });
}
function paletteRun(it) {
  if (!it || (!it.href && !it.act)) return;
  closePalette();
  if (it.act) return it.act();
  location.hash = it.href;
}

/* ------------------------------------------------------------------ 1.4: home dashboard */
function spark(points) {
  if (!points || points.length < 2) return "";
  const W = 200, H = 34, t0 = points[0][0], t1 = points[points.length - 1][0] || t0 + 1, max = Math.max(1, ...points.map((p) => p[1]));
  const xy = points.map((p) => [((p[0] - t0) / Math.max(1, t1 - t0)) * W, H - 2 - ((H - 4) * p[1]) / max]);
  const line = xy.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join("");
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><path class="a" d="${line}L${W} ${H}L0 ${H}Z"></path><path class="l" d="${line}"></path></svg>`;
}
function greeting() {
  const h = new Date().getHours();
  return h < 6 ? "Late shift" : h < 12 ? "Good morning" : h < 18 ? "Good afternoon" : "Good evening";
}
const ACTION_WORD = { kick: "kicked", warn: "warned", mute: "muted", unmute: "unmuted", ban: "banned", unban: "lifted the ban on", move: "moved",
  "undo ban": "undid the ban on", "undo mute": "undid the mute on", "report closed": "closed a report on", "report claimed": "took a report on",
  "appeal accepted": "accepted the appeal of", "appeal denied": "denied the appeal of", note: "added a note on", watch: "started watching" };

function pageHome(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Overview</p><h1>${esc(greeting())}, ${esc(S.me.name)}</h1><p class="muted" id="h-sub"></p></div>
    <div class="actions"><button class="btn" id="h-search"><span class="mag"></span> Search <kbd>Ctrl K</kbd></button>${can("server.say") ? '<button class="btn" id="h-say">Message every server</button>' : ""}</div></div>
    <div class="home-tiles" id="h-tiles"></div>
    <div class="grid grid-3"><div><div class="panel"><h3>Needs attention</h3><ul class="attention" id="h-attn"></ul></div>
        <div class="panel"><div class="head"><h3>Servers</h3><a class="small dim" href="#/servers">All servers</a></div><div id="h-servers"></div></div></div>
      <div><div class="panel"><div class="head"><h3>Latest alerts</h3><a class="small dim" href="#/alerts">All alerts</a></div><ul class="feed" id="h-alerts"></ul></div>
        <div class="panel" id="h-sus-wrap" hidden><h3>Online and worth a look</h3><ul class="feed" id="h-sus"></ul></div></div>
      <div><div class="panel"><h3>Team activity</h3><ul class="feed" id="h-act"></ul></div>
        <div class="panel" id="h-up-wrap" hidden><h3>Coming up</h3><ul class="feed" id="h-up"></ul></div></div></div>`;
  $("#h-search").onclick = openPalette;
  const say = $("#h-say");
  if (say) say.onclick = () => sayDialog("*");
  every(async () => {
    let d;
    try { d = await api("dashboard"); } catch (e) { toast(e.message, true); return; }
    const r = d.reports || { open: 0, claimed: 0, mine: 0, by_source: {} };
    const tile = (href, label, value, note, cls = "", extra = "") => `<${href ? `a href="${href}"` : "div"} class="tile ${cls}"><span class="meta">${label}</span><span class="stat">${value}</span>${extra}<span class="note">${note}</span></${href ? "a" : "div"}>`;
    const openAge = r.oldest_open ? Date.now() / 1000 - r.oldest_open : 0;
    $("#h-sub").textContent = `${d.players_online} player${d.players_online === 1 ? "" : "s"} on ${d.servers_up} of ${d.servers.length} servers right now.` +
      (d.on_duty && d.on_duty.length ? ` On duty: ${d.on_duty.map((x) => x.name).join(", ")}.` : " Nobody is on duty.");
    $("#h-tiles").innerHTML = [
      tile("#/servers", "Players online", d.players_online, `peak today ${d.peak_today} · ${d.new_players_24h} new in 24 h`, "", spark(d.spark)),
      tile("#/servers", "Servers up", `${d.servers_up}<small class="muted"> / ${d.servers.length}</small>`, d.servers_up < d.servers.length ? "some servers are not answering" : "all answering", d.servers_up < d.servers.length ? "hot" : ""),
      can("reports") ? tile("#/reports", "Open reports", r.open, `${r.claimed} in progress · ${r.mine} yours${r.oldest_open ? " · oldest " + ago(r.oldest_open).replace(" ago", "") : ""}`, openAge > 3600 ? "hot" : r.open ? "warm" : "") : "",
      tile("#/reports", "Appeals waiting", d.appeals_open, "answered by an admin who did not make the ban", d.appeals_open ? "warm" : ""),
      tile("#/alerts", "Alerts, 24 h", d.alerts_24h, d.urgent_24h ? d.urgent_24h + " urgent" : "nothing urgent", d.urgent_24h ? "hot" : ""),
      tile("#/bans", "Active bans", d.bans_active, d.bans_24h + " new in 24 h"),
      d.cases ? tile("#/cases", "Open cases", d.cases.open, d.cases.mine + " yours") : "",
    ].join("");
    const attn = [];
    for (const s of d.servers.filter((x) => !x.online)) attn.push(["bad", `<a href="#/server/${esc(s.key)}"><b>${esc(s.name)}</b> is not answering</a>`, esc(s.error || "")]);
    for (const u of d.services_down || []) attn.push(["bad", `<a href="#/health"><b>${esc(u.name)}</b> is ${esc(u.state)}</a>`, ""]);
    if (openAge > 3600) attn.push(["bad", `<a href="#/reports">A report has waited ${esc(ago(r.oldest_open).replace(" ago", ""))}</a>`, `${r.open} open`]);
    else if (r.open) attn.push(["", `<a href="#/reports">${r.open} open report${r.open > 1 ? "s" : ""}</a>`, "take one"]);
    if (d.appeals_open) attn.push(["", `<a href="#/reports">${d.appeals_open} ban appeal${d.appeals_open > 1 ? "s" : ""} waiting</a>`, ""]);
    for (const w of d.watch_online) attn.push(["", `<a href="#/player/${esc(w.pid)}">Watched: <b>${esc(w.name)}</b> is on ${esc(w.server)}</a>`, esc(w.reason || "")]);
    for (const x of d.suspicion.filter((y) => y.score >= 60)) attn.push(["bad", `<a href="#/player/${esc(x.pid)}"><b>${esc(x.name)}</b> scores ${x.score}</a>`, esc(x.server)]);
    for (const e of d.events) attn.push(["ok", `<a href="#/server/${esc(e.server)}">Event mode on ${esc(e.server)}</a>`, esc(e.note || e.by_name)]);
    if (d.backup && d.backup.stale) attn.push(["bad", `<a href="#/health">The nightly database snapshot is ${d.backup.at ? "old" : "missing"}</a>`, esc(d.backup.error || "")]);
    if ((d.disk_used_pct || 0) > 85) attn.push(["bad", `<a href="#/health">Disk ${d.disk_used_pct}% full</a>`, ""]);
    if (S.me.mfa_required && !S.me.mfa_on) attn.push(["bad", '<a href="#" data-mfa>Turn on two-step sign-in to unlock admin tools</a>', ""]);
    $("#h-attn").innerHTML = attn.map(([c, h, n]) => `<li><span class="sev ${c}"></span><span>${h}</span><span class="go dim small">${n}</span></li>`).join("")
      || '<li><span class="sev ok"></span><span>All quiet. Nothing needs you right now.</span></li>';
    const m = $("#h-attn [data-mfa]");
    if (m) m.onclick = (e) => { e.preventDefault(); accountDialog(); };
    $("#h-servers").innerHTML = d.servers.map((s) => `<a class="srv-row" href="#/server/${esc(s.key)}"><span class="n"><span class="dot ${s.online ? "on" : "off"}"></span>${esc(s.name)}</span>
      <span class="p">${s.online ? s.humans : "–"}<small> / ${s.max_players || "?"}</small></span>
      <span class="m">${s.online ? esc(s.map) + (s.mode ? " · " + esc(s.mode) : "") + (s.bots ? " · " + s.bots + " bots" : "") : "offline"}${s.needpass ? " · password" : ""}</span></a>`).join("");
    $("#h-alerts").innerHTML = d.alerts.map((a) => `<li><time>${clock(a.at)}</time><span>${a.pid ? `<a href="#/player/${esc(a.pid)}">${esc(a.title)}</a>` : esc(a.title)}</span></li>`).join("") || '<li><span></span><span class="dim">No alerts in the last 24 hours.</span></li>';
    $("#h-sus-wrap").hidden = !d.suspicion.length;
    $("#h-sus").innerHTML = d.suspicion.map((x) => `<li><span>${susTag(x.score) || x.score}</span><span><a href="#/player/${esc(x.pid)}">${esc(x.name)}</a> <span class="dim small">· ${esc(x.server)}</span><div class="dim small">${esc(x.reasons.join(" · "))}</div></span></li>`).join("");
    $("#h-act").innerHTML = d.activity.map((a) => `<li><time>${clock(a.at)}</time><span><b>${esc(a.staff)}</b> ${esc(ACTION_WORD[a.action] || a.action)} ${a.target_pid ? `<a href="#/player/${esc(a.target_pid)}">${esc(a.target)}</a>` : esc(a.target)}${a.server ? ` <span class="dim small">· ${esc(a.server)}</span>` : ""}</span></li>`).join("") || '<li><span></span><span class="dim">No staff actions yet.</span></li>';
    const label = { say: "Announcement", restart: "Match restart", map: "Map change", nextmap: "Next map" };
    $("#h-up-wrap").hidden = !d.schedule.length;
    $("#h-up").innerHTML = d.schedule.map((j) => `<li><time>${clock(j.next_at)}</time><span>${esc(label[j.action] || j.action)} <span class="dim small">· ${esc(j.server === "*" ? "every server" : j.server)}</span><div class="dim small">${esc(j.arg || "")}</div></span></li>`).join("");
  }, 10000, "home", ["alert", "reports", "action", "cases", "servers"]);
}

/* ------------------------------------------------------------------ 1.4.1: live updates */
const LIVE = { es: null, runs: new Map() };
function liveSetup() {
  if (!window.EventSource) return;
  const es = new EventSource("/api/stream");
  LIVE.es = es;
  const dot = (on) => { S.live = on; const d = $("#live-dot"); if (d) { d.classList.toggle("on", on); d.title = on ? "Live: pages update the moment something happens" : "Live updates are off: pages refresh on a timer"; } };
  es.onopen = () => dot(true);
  es.onerror = () => dot(false);
  for (const k of ["servers", "chat", "alert", "reports", "action", "cases", "anticheat", "duty"]) es.addEventListener(k, (e) => liveEvent(k, e));
}
function liveEvent(kind, e) {
  let d = {};
  try { d = JSON.parse(e.data || "{}"); } catch (err) { d = {}; }
  if (kind === "alert") liveRun("alerts", refreshAlertCount);
  if (kind === "reports" || (kind === "alert" && ["bugreport", "appeal", "reports"].includes(d.kind)) || (kind === "action" && /^(report|appeal)/.test(d.action || ""))) liveRun("reports", refreshReportCount);
  if (kind === "cases") liveRun("cases", refreshCaseCount);
  if (kind === "anticheat") liveRun("ac", refreshAcCount);
  if (kind === "duty") liveRun("duty", refreshDuty);
  for (const sub of S.subs) if (sub.page === S.page && sub.kinds.includes(kind)) liveRun(sub, sub.fn);
}
/* at most once per 1.5 s per refresher, and the last event in a burst always gets its refresh */
function liveRun(key, fn) {
  const st = LIVE.runs.get(key) || { at: 0, timer: 0 };
  LIVE.runs.set(key, st);
  if (st.timer) return;
  const wait = st.at + 1500 - Date.now();
  const go = () => { st.timer = 0; st.at = Date.now(); if (typeof key === "object" && key.page !== S.page) return; Promise.resolve(fn()).catch(() => {}); };
  if (wait <= 0) go(); else st.timer = setTimeout(go, wait);
}

/* ------------------------------------------------------------------ 1.4.1: cases */
async function refreshCaseCount() {
  if (!can("cases")) return;
  try {
    const r = await api("cases?mine=1");
    const n = r.cases.filter((c) => c.status === "open").length;
    $("#nav-cases").textContent = n;
    $("#nav-cases").hidden = !n;
  } catch (e) { /* ignore */ }
}
function caseTag(c) { return c.status === "open" ? '<span class="tag warn">Open</span>' : '<span class="tag ok">Closed</span>'; }
function newCaseDialog({ pid = "", name = "", report = 0 }) {
  modal({ title: "Open a case", sub: name ? "About " + name : "Collect reports, bans, appeals, notes and evidence about one problem in one place.", ok: "Open case",
    body: `<label>Title</label><input name="title" maxlength="120" placeholder="${esc(name ? name + ": suspected wallhack" : "Team killing ring on #2")}" value="">
      ${pid || report ? "" : '<label>Player id <span class="dim">(optional)</span></label><input name="pid" maxlength="32" class="mono" placeholder="32 hex characters">'}
      <label>What is it about</label><textarea name="summary" maxlength="2000" rows="3" placeholder="What happened, what to check"></textarea>`,
    onOk: async (f) => {
      const r = await api("cases", { title: f.title, summary: f.summary, pid: pid || (f.pid || "").trim(), name, report });
      toast("Case #" + r.id + " opened.");
      location.hash = "#/case/" + r.id;
    } });
}
function pageCases(main) {
  const state = { status: "open", mine: "" };
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Moderation</p><h1>Cases</h1></div><div class="actions"><button class="btn btn-primary" id="c-new">Open a case</button></div></div>
    <div class="tabs" id="c-tabs"><button class="btn btn-small on" data-s="open">Open</button><button class="btn btn-small" data-s="mine">Mine</button><button class="btn btn-small" data-s="closed">Closed</button><button class="btn btn-small" data-s="all">All</button></div>
    <div class="panel" id="c-list"></div>`;
  $("#c-new").onclick = () => newCaseDialog({});
  $("#c-tabs").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    for (const x of $("#c-tabs").children) x.classList.toggle("on", x === b);
    state.status = b.dataset.s === "mine" ? "open" : b.dataset.s; state.mine = b.dataset.s === "mine" ? "1" : ""; draw();
  };
  async function draw() {
    const r = await api(`cases?status=${state.status}&mine=${state.mine}`).catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    $("#c-list").innerHTML = r.cases.map((c) => `<a class="case-row" href="#/case/${c.id}"><span class="id">#${c.id}</span>
      <span><span class="t">${esc(c.title)}</span><div class="dim small">${c.name ? esc(c.name) + " · " : ""}${c.items} item${c.items === 1 ? "" : "s"} · ${c.evidence} evidence · opened by ${esc(c.created_by)} ${ago(c.created)}</div></span>
      <span class="s">${caseTag(c)}<div class="dim small">${esc(c.assignee || "nobody")} · ${ago(c.updated)}</div></span></a>`).join("") || '<p class="empty">No cases here.</p>';
  }
  every(draw, 30000, "cases", ["cases"]);
}
const ITEM_LABEL = { report: "Report", ban: "Ban", appeal: "Appeal", action: "Staff action", evidence: "Evidence", note: "Note", status: "Status" };
function caseItem(it) {
  const r = it.row;
  let body = "";
  if (it.kind === "note" || it.kind === "status") body = esc(it.text);
  else if (!r) body = '<span class="dim">This item no longer exists.</span>';
  else if (it.kind === "report") body = `<b>${esc(r.source === "auto" ? "Automatic flag" : r.source === "appeal" ? "Ban appeal" : "Player report")} #${it.ref}</b> on ${esc(r.target_name || "")} <span class="dim">· ${esc(r.server || "")} · ${esc(r.status)}</span><div>${esc(r.text)}</div>`;
  else if (it.kind === "ban") body = `<b>Ban #${r.id}</b> ${esc(r.reason)} <span class="dim">· ${esc(r.by_name)} · ${r.active ? esc(until(r.expires)) : "lifted" + (r.lifted_by ? " by " + esc(r.lifted_by) : "")}</span>`;
  else if (it.kind === "appeal") body = `<b>Appeal #${r.id}</b> <span class="dim">· ${esc(r.status)}</span><div>“${esc(r.text)}”</div>${r.answer ? `<div class="dim">${esc(r.answered_by || "")}: ${esc(r.answer)}</div>` : ""}`;
  else if (it.kind === "action") body = `<b>${esc(r.staff)}</b> ${esc(ACTION_WORD[r.action] || r.action)} ${esc(r.target)} <span class="dim">· ${esc(r.server || "")} · ${when(r.at)}</span><div class="dim">${esc(r.detail)}</div>`;
  else if (it.kind === "evidence") body = `<b>Evidence:</b> ${esc(r.title)} <span class="dim">· ${esc(r.kind)}</span>`;
  const rm = it.kind !== "status" ? `<button class="btn btn-small" data-unlink="${it.id}" title="Remove from this case">Remove</button>` : "";
  return `<li><span class="tag${it.kind === "ban" ? " bad" : it.kind === "status" ? " staff" : ""}">${ITEM_LABEL[it.kind] || esc(it.kind)}</span><div>${body}<div class="dim small">${esc(it.by_name)} · ${when(it.at)}</div></div>${rm}</li>`;
}
async function pageCase(main, id) {
  async function draw() {
    let c;
    try { c = await api("case/" + encodeURIComponent(id)); } catch (e) { main.innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
    const keep = $("#k-note") ? $("#k-note").text.value : "";
    main.innerHTML = `<div class="head"><div><p class="eyebrow"><a href="#/cases">Cases</a> · #${c.id}</p><h1>${esc(c.title)}</h1>
        <div class="tags">${caseTag(c)}${c.pid ? `<a class="tag" href="#/player/${esc(c.pid)}">${esc(c.name || c.pid)}</a>` : ""}<span class="tag">${c.assignee ? "With " + esc(c.assignee) : "Nobody has it"}</span><span class="dim small">opened by ${esc(c.created_by)} ${ago(c.created)}</span></div></div>
      <div class="actions">${c.status === "open" && c.assignee !== S.me.name ? '<button class="btn" id="k-take">Take it</button>' : ""}
        <button class="btn" id="k-edit">Edit</button>
        ${c.status === "open" ? '<button class="btn btn-primary" id="k-close">Close case</button>' : '<button class="btn" id="k-reopen">Reopen</button>'}</div></div>
      ${c.outcome && c.status === "closed" ? `<div class="banner"><span>Outcome: ${esc(c.outcome)}</span></div>` : ""}
      <div class="grid grid-2"><div>
        <div class="panel"><h3>What it is about</h3><p class="text-block">${esc(c.summary || "No summary yet.")}</p></div>
        <div class="panel"><div class="head"><h3>History</h3>${c.suggest.length ? '<button class="btn btn-small" id="k-link">Add from this player</button>' : ""}</div>
          <form id="k-note" class="chat-form"><input name="text" maxlength="2000" placeholder="Add a note to the case"><button class="btn">Add</button></form>
          <ul class="case-items" id="k-items">${c.items.map(caseItem).join("") || '<li class="dim">Nothing in this case yet.</li>'}</ul></div>
      </div><div><div class="panel" id="k-evidence"></div></div></div>`;
    $("#k-note").text.value = keep;
    $("#k-note").onsubmit = async (e) => {
      e.preventDefault();
      const text = e.target.text.value.trim(); if (!text) return;
      try { await api("case/note", { id: c.id, text }); e.target.text.value = ""; draw(); } catch (err) { toast(err.message, true); }
    };
    $("#k-items").onclick = async (e) => {
      const b = e.target.closest("button[data-unlink]"); if (!b) return;
      try { await api("case/unlink", { id: c.id, item: +b.dataset.unlink }); draw(); } catch (err) { toast(err.message, true); }
    };
    const upd = (body, msg) => api("case/update", Object.assign({ id: c.id }, body)).then(() => { toast(msg); draw(); refreshCaseCount(); });
    const take = $("#k-take");
    if (take) take.onclick = () => upd({ assignee: "me" }, "The case is yours.").catch((e) => toast(e.message, true));
    const close = $("#k-close");
    if (close) close.onclick = () => modal({ title: "Close case #" + c.id, ok: "Close case", body: '<label>Outcome</label><textarea name="o" maxlength="500" rows="3" placeholder="Banned 30 days after the demo review, appeal denied"></textarea>', onOk: (f) => upd({ status: "closed", outcome: f.o }, "Case closed.") });
    const reopen = $("#k-reopen");
    if (reopen) reopen.onclick = () => upd({ status: "open" }, "Case reopened.").catch((e) => toast(e.message, true));
    $("#k-edit").onclick = () => modal({ title: "Edit case #" + c.id, ok: "Save",
      body: `<label>Title</label><input name="title" maxlength="120" value="${esc(c.title)}"><label>What it is about</label><textarea name="summary" maxlength="2000" rows="5">${esc(c.summary || "")}</textarea>`,
      onOk: (f) => upd({ title: f.title, summary: f.summary }, "Saved.") });
    const link = $("#k-link");
    if (link) link.onclick = () => modal({ title: "Add to case #" + c.id, sub: "Reports, bans, appeals, staff actions and evidence about " + (c.name || "this player") + " that are not in the case yet.", ok: "Add",
      body: `<div class="list">${c.suggest.map((x, i) => `<label class="check"><input type="checkbox" name="s${i}"> ${esc(x.label)} <span class="dim small">· ${when(x.at)}</span></label>`).join("")}</div>`,
      onOk: async (f) => {
        for (const [k, v] of Object.entries(f)) if (v) { const x = c.suggest[+k.slice(1)]; await api("case/link", { id: c.id, kind: x.kind, ref: x.ref }); }
        draw();
      } });
    evidencePanel($("#k-evidence"), { caseId: c.id, pid: c.pid, list: c.evidence });
  }
  await draw();
  every(() => { if (!$("#modal").hidden || document.activeElement && document.activeElement.closest("#k-note")) return; draw(); }, 60000, "case/" + id, ["cases"]);
}

/* ------------------------------------------------------------------ 1.4.1: player timeline */
const TL_MOD = ["ban", "unban", "mute", "warning", "action", "ladder", "note", "case", "evidence"];
async function drawTimeline(pid) {
  let r;
  try { r = await api("timeline/" + encodeURIComponent(pid)); } catch (e) { $("#p-tl").innerHTML = `<li class="dim">${esc(e.message)}</li>`; return; }
  let filter = "", shown = 60;
  const draw = () => {
    const list = r.events.filter((e) => !filter || (filter === "mod" ? TL_MOD.includes(e.kind) : filter === "report" ? ["report", "flag", "alert"].includes(e.kind) : e.kind === filter));
    $("#p-tl").innerHTML = list.slice(0, shown).map((e) => {
      const head = e.link ? `<a href="${esc(e.link)}">${esc(e.title)}</a>` : esc(e.title);
      const extra = e.kind === "session" ? ` <span class="dim">· ${e.until ? dur(e.minutes * 60) : "playing now"}${e.chat ? " · " + e.chat + " chat line" + (e.chat === 1 ? "" : "s") : ""}</span>` : "";
      return `<li class="${esc(e.tone || "")} ${e.kind === "session" ? "session" : ""}"><div class="when">${when(e.at)}${e.server && e.kind !== "session" ? " · " + esc(e.server) : ""}${e.by ? " · " + esc(e.by) : ""}</div>
        <div><span class="what">${head}</span>${extra}</div>${e.detail ? `<div class="det">${esc(e.detail)}</div>` : ""}</li>`;
    }).join("") || '<li class="dim">Nothing recorded.</li>';
    $("#p-tl-more").hidden = list.length <= shown;
  };
  $("#p-tl-tabs").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    for (const x of $("#p-tl-tabs").children) x.classList.toggle("on", x === b);
    filter = b.dataset.f; shown = 60; draw();
  };
  $("#p-tl-more").onclick = () => { shown += 100; draw(); };
  draw();
}

/* ------------------------------------------------------------------ 1.4.1: evidence locker */
function readFile(file) {
  return new Promise((ok, bad) => { const fr = new FileReader(); fr.onload = () => ok(String(fr.result).split(",")[1] || ""); fr.onerror = () => bad(new Error("Could not read that file.")); fr.readAsDataURL(file); });
}
function evidenceCard(e) {
  const del = can("evidence.delete") ? `<button class="btn btn-small" data-ev-del="${e.id}">Remove</button>` : "";
  let body = "";
  if (e.kind === "image") body = `<a href="/api/evidence/file?id=${e.id}" target="_blank" rel="noopener"><img src="/api/evidence/file?id=${e.id}" alt="${esc(e.title)}" loading="lazy"></a>`;
  else if (e.kind === "demo") body = `<a class="btn btn-small" href="/api/evidence/file?id=${e.id}">Download demo</a><span class="d">${e.text ? "jump to " + dur(e.text.offset_s) : ""} · ${(e.size / 1048576).toFixed(1)} MB</span>`;
  else if (e.kind === "chat") body = `<button class="btn btn-small" data-ev-chat="${e.id}">Read ${Array.isArray(e.text) ? e.text.length : 0} lines</button>`;
  else if (e.kind === "link") body = `<a href="${esc(e.text)}" target="_blank" rel="noopener noreferrer" class="small">${esc(e.text.replace(/^https:\/\//, "").slice(0, 60))}</a>`;
  else body = `<span class="d">${esc(String(e.text || "").slice(0, 200))}</span>`;
  return `<div class="ev"><span class="t">${esc(e.title)}</span>${body}<span class="d">${esc(e.by_name)} · ${when(e.at)}${e.case_id ? ` · <a href="#/case/${e.case_id}">case #${e.case_id}</a>` : ""}</span>${del}</div>`;
}
async function evidencePanel(el, { caseId = 0, pid = "", list = null }) {
  if (!el) return;
  if (!list) {
    try { list = (await api(caseId ? "evidence?case=" + caseId : "evidence?pid=" + encodeURIComponent(pid))).evidence; } catch (e) { el.innerHTML = `<h3>Evidence</h3><p class="dim">${esc(e.message)}</p>`; return; }
  }
  const reload = () => evidencePanel(el, { caseId, pid });
  el.innerHTML = `<div class="head"><h3>Evidence</h3><div class="actions">
      <button class="btn btn-small" data-ev-add="image">Screenshot</button><button class="btn btn-small" data-ev-add="chat">Chat excerpt</button>
      <button class="btn btn-small" data-ev-add="link">Link</button><button class="btn btn-small" data-ev-add="text">Statement</button></div></div>
    <div class="ev-grid">${list.map(evidenceCard).join("") || '<p class="dim">No evidence yet. Screenshots, server demos (from a report), chat and links stay here.</p>'}</div>`;
  el.onclick = async (e) => {
    const add = e.target.closest("button[data-ev-add]");
    const del = e.target.closest("button[data-ev-del]");
    const chat = e.target.closest("button[data-ev-chat]");
    if (chat) {
      const ev = list.find((x) => x.id === +chat.dataset.evChat);
      return modal({ title: ev.title, ok: "Close", body: `<div class="chat-log chat-excerpt">${(ev.text || []).map((l) => `<div class="chat-line ${esc(l.kind)}"><time>${clock(l.at)}</time><span class="srv">${esc(l.server)}</span><span class="who">${esc(l.name)}:</span> ${esc(l.text)}</div>`).join("")}</div>`, onOk: () => {} });
    }
    if (del) return modal({ title: "Remove evidence", sub: "The file is deleted for good. The audit log keeps that you removed it.", ok: "Remove", danger: true,
      body: '<label>Why</label><input name="reason" maxlength="200">', onOk: async (f) => { await api("evidence/delete", { id: +del.dataset.evDel, reason: f.reason }); reload(); } });
    if (!add) return;
    const base = { case: caseId || undefined, pid: pid || undefined };
    const kind = add.dataset.evAdd;
    if (kind === "image") return modal({ title: "Add a screenshot", sub: "JPEG, PNG or WebP, up to 8 MB.", ok: "Upload",
      body: '<label>Title</label><input name="title" maxlength="160" placeholder="Wall-tracking through the train hall"><label>Picture</label><input type="file" name="file" accept="image/jpeg,image/png,image/webp">',
      onOk: async () => {
        const f = $("#modal-body input[type=file]").files[0];
        if (!f) throw new Error("Pick a picture first.");
        if (f.size > 8 * 1024 * 1024) throw new Error("That picture is bigger than 8 MB.");
        await api("evidence", Object.assign({ kind: "image", title: $("#modal-body [name=title]").value, data: await readFile(f) }, base));
        toast("Saved."); reload();
      } });
    if (kind === "chat") {
      const servers = S.servers.length ? S.servers : await loadServers().catch(() => []);
      return modal({ title: "Save a chat excerpt", sub: "Keeps a copy of the chat around a moment, so it outlives the 30-day chat history.", ok: "Save",
        body: `<label>Around</label><input type="datetime-local" name="at" value="${localInput(Date.now() / 1000)}"><label>Minutes either side</label><input name="minutes" type="number" min="1" max="60" value="10">
          <label>From</label><select name="server">${pid ? '<option value="">Only this player\'s lines</option>' : ""}${servers.map((x) => `<option value="${esc(x.key)}">Everything on ${esc(x.name)}</option>`).join("")}</select>
          <label>Title <span class="dim">(optional)</span></label><input name="title" maxlength="160">`,
        onOk: async (f) => { await api("evidence", Object.assign({ kind: "chat", at: Math.floor(new Date(f.at).getTime() / 1000), minutes: +f.minutes, server: f.server, title: f.title }, base)); toast("Saved."); reload(); } });
    }
    if (kind === "link") return modal({ title: "Add a link", sub: "A clip, a forum post or anything else on the web.", ok: "Add",
      body: '<label>Link</label><input name="url" maxlength="500" placeholder="https://"><label>Title</label><input name="title" maxlength="160">',
      onOk: async (f) => { await api("evidence", Object.assign({ kind: "link", url: f.url.trim(), title: f.title }, base)); reload(); } });
    if (kind === "text") return modal({ title: "Add a statement", sub: "What a player or staff member told you, in their words.", ok: "Add",
      body: '<label>Title</label><input name="title" maxlength="160" placeholder="Statement from the reporter"><label>Text</label><textarea name="text" rows="6" maxlength="4000"></textarea>',
      onOk: async (f) => { await api("evidence", Object.assign({ kind: "text", title: f.title, text: f.text }, base)); reload(); } });
  };
}

/* ------------------------------------------------------------------ 1.4.2: anti-cheat queue count, duty, push */
async function refreshAcCount() {
  if (!can("anticheat")) return;
  try {
    const r = await api("anticheat");
    const n = (r.counts && r.counts.open) || 0;
    $("#nav-ac").textContent = n;
    $("#nav-ac").hidden = !n;
  } catch (e) { /* ignore */ }
}
async function refreshDuty() {
  const b = $("#duty");
  if (!b || !can("duty")) return;
  let r;
  try { r = await api("duty"); } catch (e) { return; }
  S.duty = r;
  b.hidden = false;
  b.classList.toggle("on", r.me.on);
  b.textContent = r.me.on ? `On duty until ${clock(r.me.until)}` : "Go on duty";
  b.title = r.on_duty.length ? "On duty now: " + r.on_duty.map((d) => d.name).join(", ") : "Nobody is on duty";
  b.onclick = () => {
    if (r.me.on) return api("duty", { on: false }).then(() => { toast("You are off duty."); refreshDuty(); }).catch((e) => toast(e.message, true));
    modal({ title: "Go on duty", sub: "While you are on duty, every alert reaches your devices, not only urgent ones. It switches off by itself.", ok: "Go on duty",
      body: `<label>For</label><select name="hours"><option value="1">1 hour</option><option value="2">2 hours</option><option value="4" selected>4 hours</option><option value="8">8 hours</option></select>
        ${r.devices ? "" : '<p class="muted">No device of yours gets alerts yet. Turn them on under your name, "Alerts on this device".</p>'}`,
      onOk: async (f) => { await api("duty", { on: true, hours: +f.hours }); toast("You are on duty."); refreshDuty(); } });
  };
}
function b64ToBytes(s) {
  const pad = "=".repeat((4 - (s.length % 4)) % 4);
  const raw = atob((s + pad).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (c) => c.charCodeAt(0));
}
async function pushDialog() {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window))
    throw new Error("This browser cannot show notifications. On an iPhone, first add the portal to the home screen (Share, Add to Home Screen) and open it from there.");
  const reg = await navigator.serviceWorker.register("/sw.js");
  await navigator.serviceWorker.ready;
  const sub = await reg.pushManager.getSubscription();
  const body = `<p>${sub ? '<span class="tag ok">On</span> This device gets staff alerts.' : '<span class="tag">Off</span> This device gets no alerts.'}</p>
    <p class="muted">Urgent alerts (a server down, a ban dodger, a very high suspicion score) always arrive. Everything else arrives while you are on duty. Notifications show the alert title only after your device asks the portal, so nothing about players passes through Google, Apple or Mozilla.</p>`;
  setTimeout(() => modal({ title: "Alerts on this device", ok: sub ? "Turn off" : "Turn on", danger: !!sub, body: body + (sub ? '<p><button type="button" class="btn btn-small" data-push-test>Send a test</button></p>' : ""),
    onOk: async () => {
      if (sub) { await api("push/unsubscribe", { endpoint: sub.endpoint }); await sub.unsubscribe(); toast("Alerts are off on this device."); return; }
      if ((await Notification.requestPermission()) !== "granted") throw new Error("Notifications are blocked for this site. Allow them in the browser settings.");
      const key = (await api("push/key")).key;
      const s = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToBytes(key) });
      await api("push/subscribe", { endpoint: s.endpoint });
      toast("Alerts are on for this device.");
      refreshDuty();
    } }), 0);
  setTimeout(() => {
    const t = $("#modal-body [data-push-test]");
    if (t) t.onclick = async () => { try { const r = await api("push/test", {}); toast(r.sent ? "Test sent." : "The test did not go out. Turn alerts off and on again."); } catch (e) { toast(e.message, true); } };
  }, 10);
}

/* ------------------------------------------------------------------ 1.4.2: per-person rights */
const PERM_LABEL = { "view": "See the portal", "chat.reply": "Reply in chat", "player.kick": "Kick", "player.warn": "Warn", "player.mute": "Mute", "player.move": "Move players",
  "ban.temp": "Timed bans (up to a day)", "ban.perm": "Long and permanent bans", "ban.remove": "Lift bans", "server.say": "Announce", "server.map": "Change map",
  "server.restart": "Restart matches", "reports": "Reports", "lookup": "Player lookup", "lookup.ip": "IP addresses", "audit": "Audit log", "staff.manage": "Manage staff",
  "health": "Health page", "health.restart": "Restart game servers", "punish": "Punishment ladder", "watch": "Watchlist", "filters.manage": "Edit chat filter",
  "templates.manage": "Edit saved replies", "appeals.answer": "Answer appeals", "schedule": "Schedule", "event": "Event mode", "livemap": "Live map", "cvars": "Server settings",
  "review": "Stats review", "weekly": "Weekly report", "insights": "Website insights", "backup": "Database snapshot", "cases": "Cases", "evidence": "Evidence",
  "evidence.delete": "Remove evidence", "history": "Player history", "quality": "Moderator quality", "anticheat": "Anti-cheat queue", "duty": "Go on duty", "2fa.reset": "Reset two-step sign-in" };
const RANKS = ["trial", "moderator", "admin", "owner"];
async function rightsDialog(id, done) {
  const r = await api("staff/rights?id=" + encodeURIComponent(id));
  const role = r.role || "moderator";
  const base = (p) => RANKS.indexOf(role) >= RANKS.indexOf(r.perms[p]);
  const rows = Object.keys(r.perms).filter((p) => p !== "2fa.reset" && p !== "staff.manage").map((p) => {
    const v = r.add.includes(p) ? "add" : r.remove.includes(p) ? "remove" : "";
    return `<span>${esc(PERM_LABEL[p] || p)} <span class="dim small">· ${base(p) ? "with the role" : esc(r.perms[p]) + " and up"}</span></span>
      <select name="p:${esc(p)}"><option value="">${base(p) ? "Yes (role)" : "No (role)"}</option>${base(p) ? '<option value="remove">Take away</option>' : '<option value="add">Give</option>'}</select>`.replace(`value="${v}"`, `value="${v}" selected`);
  }).join("");
  const presets = Object.entries(r.presets).map(([k, x]) => `<button type="button" class="btn btn-small" data-preset="${esc(k)}">${esc(x.label)}</button>`).join(" ");
  modal({ title: "Rights for " + (r.name || id), sub: `Role: ${role}${r.role ? "" : " (from Discord)"}. Extras here add to or take from the role. Admin tools still need two-step sign-in.`, ok: "Save",
    body: `<p class="tags">${presets} <button type="button" class="btn btn-small" data-preset="">Clear</button></p><div class="rights">${rows}</div>`,
    onOk: async (f) => {
      const add = [], remove = [];
      for (const [k, v] of Object.entries(f)) if (k.startsWith("p:") && v) (v === "add" ? add : remove).push(k.slice(2));
      await api("staff/rights", { discord_id: id, add, remove });
      toast("Rights saved."); if (done) done();
    } });
  $("#modal-body").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-preset]"); if (!b) return;
    const p = r.presets[b.dataset.preset] || {};
    for (const sel of $("#modal-body").querySelectorAll("select[name^='p:']")) {
      const perm = sel.name.slice(2);
      const want = (p.perms || []).includes(perm) ? "add" : (p.remove || []).includes(perm) ? "remove" : "";
      if (!b.dataset.preset) sel.value = "";
      else if (want && [...sel.options].some((o) => o.value === want)) sel.value = want;
    }
  });
}

/* ------------------------------------------------------------------ 1.4.2: player history */
function lineChart(points, bucket) {
  if (!points.length) return '<p class="empty">No samples yet. The portal records player counts every five minutes.</p>';
  const W = 900, H = 220, L = 34, B = 22, top = 10;
  const t0 = points[0].t, t1 = points[points.length - 1].t || t0 + 1;
  const max = Math.max(4, ...points.map((p) => p.peak));
  const x = (t) => L + ((t - t0) / Math.max(1, t1 - t0)) * (W - L - 8);
  const y = (v) => top + (1 - v / max) * (H - top - B);
  const avg = points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.avg).toFixed(1)}`).join("");
  const peak = `M${x(t0)},${y(0)}` + points.map((p) => `L${x(p.t).toFixed(1)},${y(p.peak).toFixed(1)}`).join("") + `L${x(t1)},${y(0)}Z`;
  const ticks = [0, Math.round(max / 2), max].map((v) => `<line x1="${L}" x2="${W}" y1="${y(v)}" y2="${y(v)}"/><text x="2" y="${y(v) + 4}">${v}</text>`).join("");
  const days = Math.round((t1 - t0) / 86400);
  const labels = [0, 0.25, 0.5, 0.75, 1].map((f) => { const t = t0 + f * (t1 - t0); const d = new Date(t * 1000);
    return `<text x="${x(t) - 18}" y="${H - 4}">${days > 2 ? d.toLocaleDateString(undefined, { day: "2-digit", month: "short" }) : d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" })}</text>`; }).join("");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="Players online over time"><g class="grid">${ticks}</g><path class="peak" d="${peak}"/><path class="avg" d="${avg}"/>${labels}</svg>
    <p class="dim small">Line: average players per ${bucket >= 3600 ? bucket / 3600 + " h" : bucket / 60 + " min"}. Shade: the peak in that time.</p>`;
}
function pageHistory(main) {
  const st = { days: 7, server: "" };
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Insights</p><h1>Player history</h1><p class="muted" id="hi-sub"></p></div></div>
    <div class="tabs" id="hi-days"><button class="btn btn-small" data-d="1">24 hours</button><button class="btn btn-small on" data-d="7">7 days</button><button class="btn btn-small" data-d="30">30 days</button><button class="btn btn-small" data-d="90">90 days</button></div>
    <div class="tabs" id="hi-srv"><button class="btn btn-small on" data-s="">All servers</button></div>
    <div class="panel"><h3>Players online</h3><div id="hi-chart"></div></div>
    <div class="grid grid-2"><div class="panel"><h3>Busiest hours <span class="dim small">(Belgian time, average players)</span></h3><div id="hi-heat"></div></div>
      <div><div class="panel"><h3>Servers</h3><div class="table-wrap" id="hi-servers"></div></div><div class="panel"><h3>Maps by average players</h3><div class="bars" id="hi-maps"></div></div></div></div>`;
  loadServers().then((list) => { $("#hi-srv").innerHTML += list.map((x) => `<button class="btn btn-small" data-s="${esc(x.key)}">${esc(x.name)}</button>`).join(""); }).catch(() => {});
  const tabs = (id, key, attr) => $(id).onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $(id).children) x.classList.toggle("on", x === b); st[key] = attr === "d" ? +b.dataset.d : b.dataset.s; draw(); };
  tabs("#hi-days", "days", "d");
  tabs("#hi-srv", "server", "s");
  async function draw() {
    let r;
    try { r = await api(`history?days=${st.days}&server=${encodeURIComponent(st.server)}`); } catch (e) { toast(e.message, true); return; }
    const pk = Math.max(0, ...r.points.map((p) => p.peak));
    $("#hi-sub").textContent = `${r.samples} samples · highest ${pk} players at once in this period.`;
    $("#hi-chart").innerHTML = lineChart(r.points, r.bucket);
    const max = Math.max(1, ...r.heatmap.flat().filter((v) => v != null));
    const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    $("#hi-heat").innerHTML = `<div class="heat"><span class="h"></span>${[...Array(24).keys()].map((h) => `<span class="h">${h % 3 ? "" : h}</span>`).join("")}
      ${r.heatmap.map((row, d) => `<span class="d">${DAYS[d]}</span>${row.map((v, h) => `<span title="${DAYS[d]} ${h}:00 · ${v == null ? "no data" : v + " players"}" data-a="${v == null ? "" : (0.08 + 0.92 * v / max).toFixed(2)}"></span>`).join("")}`).join("")}</div>`;
    for (const c of document.querySelectorAll("#hi-heat [data-a]")) if (c.dataset.a) c.style.background = `rgba(91,155,213,${c.dataset.a})`;
    $("#hi-servers").innerHTML = `<table><tr><th>Server</th><th class="num">Uptime</th><th class="num">Average</th><th class="num">Peak</th></tr>${r.servers.map((x) => `<tr><td>${esc(x.name)}</td><td class="num">${x.uptime_pct == null ? "–" : x.uptime_pct + "%"}</td><td class="num">${x.avg}</td><td class="num">${x.peak}</td></tr>`).join("")}</table>`;
    const mm = Math.max(1, ...r.maps.map((m) => m.avg));
    $("#hi-maps").innerHTML = r.maps.map((m) => `<div class="bar"><span>${esc(m.map)}</span><i data-w="${Math.max(2, (100 * m.avg) / mm).toFixed(0)}"></i><span class="dim small">${m.avg} · ${m.hours} h</span></div>`).join("") || '<p class="dim">No maps recorded.</p>';
    for (const i of document.querySelectorAll("#hi-maps i[data-w]")) i.style.width = i.dataset.w + "%";
  }
  every(draw, 300000, "history");
}

/* ------------------------------------------------------------------ 1.4.2: moderator quality */
function pageQuality(main) {
  let days = 30;
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Admin</p><h1>Moderator quality</h1><p class="muted">What each staff member did, how fast reports were picked up, and how often their bans held. A starting point for a talk, not a score.</p></div></div>
    <div class="tabs" id="q-days"><button class="btn btn-small" data-d="7">7 days</button><button class="btn btn-small on" data-d="30">30 days</button><button class="btn btn-small" data-d="90">90 days</button></div>
    <div class="cards" id="q-team"></div><div class="panel table-wrap" id="q-list"></div>`;
  $("#q-days").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#q-days").children) x.classList.toggle("on", x === b); days = +b.dataset.d; draw(); };
  const mins = (m) => m == null ? "–" : m < 60 ? Math.round(m) + " min" : (m / 60).toFixed(1) + " h";
  async function draw() {
    let r;
    try { r = await api("quality?days=" + days); } catch (e) { toast(e.message, true); return; }
    const t = r.team;
    $("#q-team").innerHTML = [["Reports in", t.reports, ""], ["Left over a day", t.untouched, t.untouched ? "warm" : ""], ["Appeals", t.appeals, ""], ["Appeals accepted", t.accepted, ""]]
      .map(([k, v, c]) => `<div class="card ${c}"><div class="meta">${k}</div><div class="big">${v}</div></div>`).join("");
    $("#q-list").innerHTML = r.staff.length ? `<table><tr><th>Staff</th><th class="num">Actions</th><th class="num">Bans</th><th class="num">Kicks</th><th class="num">Mutes</th><th class="num">Warns</th>
      <th class="num">Reports closed</th><th class="num">Time to take</th><th class="num">Time to close</th><th class="num">Bans overturned</th><th class="num">Lifted by others</th><th class="num">Undos</th><th class="num">Appeals answered</th><th class="num">Cases closed</th></tr>
      ${r.staff.map((x) => `<tr><td>${esc(x.name)}</td><td class="num">${x.actions}</td><td class="num">${x.bans}</td><td class="num">${x.kicks}</td><td class="num">${x.mutes}</td><td class="num">${x.warns}</td>
        <td class="num">${x.reports_closed}</td><td class="num">${mins(x.take_median_min)}</td><td class="num">${mins(x.close_median_min)}</td>
        <td class="num">${x.bans_overturned}${x.overturn_pct != null ? ` <span class="dim small">${x.overturn_pct}%</span>` : ""}</td><td class="num">${x.bans_lifted}</td><td class="num">${x.undos}</td><td class="num">${x.appeals_answered}</td><td class="num">${x.cases_closed}</td></tr>`).join("")}</table>
      <p class="dim small">Times are medians from a report arriving. Overturned: bans lifted on appeal.</p>` : '<p class="empty">No staff activity in this period.</p>';
  }
  draw();
}

/* ------------------------------------------------------------------ 1.4.2: anti-cheat review queue */
function pageAnticheat(main) {
  let status = "open";
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Moderation</p><h1>Anti-cheat queue</h1><p class="muted">Anti-cheat detections, very high suspicion scores and ban dodgers in one list, strongest first. Clear it, act on it or open a case.</p></div></div>
    <div class="tabs" id="ac-tabs"><button class="btn btn-small on" data-s="open">To review</button><button class="btn btn-small" data-s="done">Done</button></div>
    <div class="panel" id="ac-list"></div>`;
  $("#ac-tabs").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#ac-tabs").children) x.classList.toggle("on", x === b); status = b.dataset.s; draw(); };
  $("#ac-list").onclick = (e) => {
    const b = e.target.closest("button[data-ac]"); if (!b) return;
    const id = +b.dataset.ac, out = b.dataset.out;
    if (out === "case") return api("anticheat", { id, outcome: "case" }).then(() => newCaseDialog({ pid: b.dataset.pid, name: b.dataset.name })).catch((err) => toast(err.message, true));
    if (out === "open") return api("anticheat", { id, outcome: "open" }).then(draw).catch((err) => toast(err.message, true));
    modal({ title: out === "cleared" ? "Clear " + b.dataset.name : "Mark as acted on", ok: out === "cleared" ? "Clear" : "Done",
      body: `<label>Note</label><input name="note" maxlength="300" placeholder="${out === "cleared" ? "Watched the demo, clean" : "Banned permanently, case #12"}">`,
      onOk: async (f) => { await api("anticheat", { id, outcome: out, note: f.note }); draw(); } });
  };
  async function draw() {
    let r;
    try { r = await api("anticheat?status=" + status); } catch (e) { toast(e.message, true); return; }
    $("#ac-list").innerHTML = r.items.map((x) => `<div class="case-row"><span class="id">${x.score || "–"}</span>
      <span><span class="t"><a href="#/player/${esc(x.pid)}">${esc(x.name || x.pid)}</a></span> <span class="tag ${x.kind === "detection" || x.kind === "dodger" ? "bad" : "warn"}">${esc(x.label)}</span>
        ${x.online ? `<a class="tag ok" href="#/server/${esc(x.online)}">Online on ${esc(x.online)}</a>` : ""}${x.banned ? '<span class="tag bad">Banned</span>' : ""}${x.suspicion != null ? " " + susTag(x.suspicion) : ""}
        <div class="dim small">${esc(x.detail)} · ${esc(x.server || "")} · ${ago(x.at)}</div>${x.status !== "open" ? `<div class="small">${esc(x.status)} by ${esc(x.by_name || "")}${x.note ? ": " + esc(x.note) : ""}</div>` : ""}</span>
      <span class="s">${x.status === "open" ? `<button class="btn btn-small" data-ac="${x.id}" data-out="cleared" data-name="${esc(x.name)}">Clear</button> <button class="btn btn-small" data-ac="${x.id}" data-out="actioned" data-name="${esc(x.name)}">Acted on</button> ${can("cases") ? `<button class="btn btn-small" data-ac="${x.id}" data-out="case" data-pid="${esc(x.pid)}" data-name="${esc(x.name)}">Case</button>` : ""}` : `<button class="btn btn-small" data-ac="${x.id}" data-out="open">Reopen</button>`}</span></div>`).join("") || '<p class="empty">Nothing to review.</p>';
  }
  every(draw, 30000, "anticheat", ["anticheat"]);
}

boot();

/* ------------------------------------------------------------------ devlog comments (truecombat.eu, accounts service) */
const SITE = "https://truecombat.eu/";
const CM_REASON = { new: "First comment, no linked PC", filter: "Word filter", link: "Link from an account with no linked PC",
  reports: "Hidden by player reports", staff: "Hidden by staff" };
const CM_REPORT = { spam: "Spam", abuse: "Abuse", cheats: "Cheats or exploits", other: "Something else" };
function cmAge(t) {
  const d = Math.floor((Date.now() / 1000 - t) / 86400);
  return d < 1 ? "made today" : d < 60 ? d + " days old" : Math.round(d / 30) + " months old";
}
function cmCard(c) {
  const a = c.author || null;
  const reports = c.reports || [];
  const tags = [];
  if (c.state === "held") tags.push(`<span class="tag warn">Held: ${esc(CM_REASON[c.reason] || c.reason)}</span>`);
  if (c.state === "hidden") tags.push(`<span class="tag bad">${esc(CM_REASON[c.reason] || "Hidden")}</span>`);
  if (c.state === "removed") tags.push(`<span class="tag bad">Removed by ${esc(c.moderatedBy || "staff")}</span>`);
  if (c.state === "live" && reports.length) tags.push(`<span class="tag warn">${reports.length} report${reports.length > 1 ? "s" : ""}</span>`);
  if (c.state === "live" && !reports.length) tags.push('<span class="tag ok">Live</span>');
  const kinds = [...new Set(reports.map((r) => r.reason))];
  for (const k of kinds) tags.push(`<span class="tag">${esc(CM_REPORT[k] || k)}</span>`);
  if (c.pinned) tags.push('<span class="tag staff">Pinned</span>');
  if (c.parent) tags.push('<span class="tag">Reply</span>');
  if (a && a.team) tags.push('<span class="tag staff">Team Terminus</span>');
  const facts = a ? [cmAge(a.created), a.matches + " matches", a.pc ? "linked PC" : "no linked PC", a.badges.includes("clean") ? "clean record" : "",
    a.today > 1 ? a.today + " comments today" : "", a.paused ? (a.paused === -1 ? "comments paused for good" : "paused, " + until(a.paused)) : ""].filter(Boolean).join(" · ")
    : "Account deleted";
  const who = reports.length ? " · reported by " + reports.map((r) => esc(r.name || "a deleted account") + (r.note ? ` (“${esc(r.note)}”)` : "")).join(", ") : "";
  const b = (label, action, cls = "") => `<button class="btn btn-small ${cls}" data-cm="${c.id}" data-do="${action}">${label}</button>`;
  const btns = [];
  if (c.state === "held") btns.push(b("Publish", "publish"), b("Remove", "remove", "btn-danger"));
  else if (c.state === "hidden") btns.push(b("Keep it hidden", "keep"), b("Restore", "restore"), b("Remove", "remove", "btn-danger"));
  else if (c.state === "removed") btns.push(b("Restore", "restore"));
  else {
    if (reports.length) btns.push(b("No action", "dismiss"));
    btns.push(b("Hide", "hide"), b("Remove", "remove", "btn-danger"));
    if (!c.parent) btns.push(b(c.pinned ? "Unpin" : "Pin", c.pinned ? "unpin" : "pin"));
    btns.push(b("Reply as team", "reply"));
  }
  if (a && !a.team) btns.push(a.paused ? `<button class="btn btn-small" data-cm-unpause="${esc(a.account)}" data-name="${esc(a.name)}">Unpause</button>`
    : `<button class="btn btn-small btn-danger" data-cm-pause="${esc(a.account)}" data-name="${esc(a.name)}">Pause commenting</button>`);
  const name = a ? (a.statsId ? `<a href="${SITE}player?id=${esc(a.statsId)}" target="_blank" rel="noopener">${esc(a.name)}</a>` : esc(a.name)) : "<span class=\"dim\">deleted account</span>";
  return `<div class="panel cm-card"><div class="head"><div><div class="tags">${tags.join("")}</div>
    <h2 class="cm-who">${name} <span class="muted cm-on">on <a href="${SITE}devlog-${esc(c.post)}.html#comments" target="_blank" rel="noopener">${esc(c.post)}</a> · ${ago(c.at)}${c.edited ? " · edited" : ""}${c.likes ? " · " + c.likes + " ♥" : ""}</span></h2>
    <span class="muted">${facts}${who}</span></div><div class="actions">${btns.join("")}</div></div>
    <p class="cm-text">${esc(c.text || "")}</p></div>`;
}
function pageComments(main) {
  const state = { tab: "needs", q: "", post: "" };
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Moderation</p><h1>Devlog comments</h1></div>
    <div class="actions">${can("comments.close") ? '<button class="btn btn-small" id="cm-close">Close or open a post</button>' : ""}</div></div>
    <div class="cards cm-stats" id="cm-stats"></div>
    <div class="tabs" id="cm-tabs"><button class="btn btn-small on" data-t="needs">Needs a look</button><button class="btn btn-small" data-t="recent">All recent</button><button class="btn btn-small" data-t="hidden">Hidden and removed</button><button class="btn btn-small" data-t="paused">Paused players</button></div>
    <div class="cm-filter"><input id="cm-q" placeholder="Player name" maxlength="40" autocomplete="off"><input id="cm-post" placeholder="Post (slug), e.g. inside-0372" maxlength="80" autocomplete="off"></div>
    <div id="cm-list"><p class="empty">Loading…</p></div>`;
  $("#cm-tabs").onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    for (const x of $("#cm-tabs").children) x.classList.toggle("on", x === b);
    state.tab = b.dataset.t; draw();
  };
  let timer = 0;
  for (const id of ["#cm-q", "#cm-post"]) $(id).oninput = () => { clearTimeout(timer); timer = setTimeout(() => { state.q = $("#cm-q").value.trim(); state.post = $("#cm-post").value.trim(); draw(); }, 250); };
  if ($("#cm-close")) $("#cm-close").onclick = () => modal({ title: "Close or open comments on a post", ok: "Save",
    sub: "Closed posts keep their comments readable; nobody can add new ones. Front matter comments: off does the same from the site.",
    body: '<label>Post (slug)</label><input name="post" required maxlength="80" placeholder="inside-0372"><label><input type="checkbox" name="closed" checked> Closed</label>',
    onOk: async (f) => { const r = await api("comments/close", { post: f.post.trim(), closed: !!f.closed }); toast(r.closed ? "Comments closed on " + r.post + "." : "Comments open on " + r.post + "."); stats(); } });
  $("#cm-list").onclick = async (e) => {
    const pz = e.target.closest("button[data-cm-pause]");
    if (pz) return modal({ title: "Pause commenting", sub: pz.dataset.name + " can still read and like, but can't post or edit comments until the pause ends.", ok: "Pause", danger: true,
      body: '<label>How long</label><select name="days"><option value="1">1 day</option><option value="7" selected>7 days</option><option value="30">30 days</option><option value="0">For good</option></select><label>Reason (staff only)</label><input name="reason" maxlength="200" placeholder="Repeated spam">',
      onOk: async (f) => { await api("comments/pause", { account: pz.dataset.cmPause, days: +f.days, reason: f.reason }); toast(pz.dataset.name + " paused."); draw(); stats(); } });
    const up = e.target.closest("button[data-cm-unpause]");
    if (up) { await api("comments/unpause", { account: up.dataset.cmUnpause, name: up.dataset.name }).then(() => { toast("Pause lifted."); draw(); stats(); }, (err) => toast(err.message, true)); return; }
    const b = e.target.closest("button[data-cm]"); if (!b) return;
    const id = +b.dataset.cm, act = b.dataset.do;
    if (act === "reply") return modal({ title: "Reply as team", sub: "Posted under your own TrueCombat account with the Team Terminus tag, straight away.", ok: "Post reply",
      body: '<label>Reply</label><textarea name="text" maxlength="1000" required></textarea>',
      onOk: async (f) => { await api("comments/reply", { parent: id, text: f.text }); toast("Reply posted."); draw(); } });
    if (act === "remove") return modal({ title: "Remove this comment", sub: "It disappears from the site. The text stays here for 90 days in case of an appeal.", ok: "Remove", danger: true,
      onOk: async () => { await api("comments/act", { id, action: "remove" }); toast("Comment removed."); draw(); stats(); } });
    try {
      await api("comments/act", { id, action: act === "keep" ? "hide" : act });
      toast({ publish: "Published. The author's next comments post straight away.", hide: "Hidden.", restore: "Restored.", dismiss: "Reports closed.", pin: "Pinned on the post.", unpin: "Unpinned.", keep: "Kept hidden, reports closed." }[act] || "Done.");
      draw(); stats();
    } catch (err) { toast(err.message, true); }
  };
  async function stats() {
    try {
      const s = await api("comments/stats");
      const tile = (label, n, sub) => `<div class="card"><div class="meta">${label}</div><div class="big">${n}${sub ? ` <small>${sub}</small>` : ""}</div></div>`;
      $("#cm-stats").innerHTML = tile("Reported or hidden", s.reported + s.hidden) + tile("Held for a check", s.held) +
        tile("New today", s.today, s.todayPosts ? "on " + s.todayPosts + " post" + (s.todayPosts > 1 ? "s" : "") : "") + tile("Paused players", s.paused);
      const n = $("#nav-comments"); if (n) { n.textContent = s.needs; n.hidden = !s.needs; }
    } catch (err) { $("#cm-stats").innerHTML = `<p class="error">${esc(err.message)}</p>`; }
  }
  async function draw() {
    let r;
    try { r = await api("comments?tab=" + state.tab + "&q=" + encodeURIComponent(state.q) + "&post=" + encodeURIComponent(state.post)); }
    catch (err) { $("#cm-list").innerHTML = `<p class="error">${esc(err.message)}</p>`; return; }
    if (state.tab === "paused") {
      $("#cm-list").innerHTML = (r.paused || []).map((p) => `<div class="panel cm-card"><div class="head"><div><h2 class="cm-who">${esc(p.name)}</h2>
        <span class="muted">${p.until === -1 ? "For good" : until(p.until)} · by ${esc(p.by || "staff")} · ${ago(p.at)}${p.reason ? " · " + esc(p.reason) : ""}</span></div>
        <div class="actions"><button class="btn btn-small" data-cm-unpause="${esc(p.account)}" data-name="${esc(p.name)}">Unpause</button></div></div></div>`).join("") || '<p class="empty">Nobody is paused.</p>';
      return;
    }
    $("#cm-list").innerHTML = (r.comments || []).map(cmCard).join("") || `<p class="empty">${state.tab === "needs" ? "Nothing waiting. Good." : "No comments here."}</p>`;
  }
  stats();
  every(draw, 30000, "comments");
}
async function refreshCommentCount() {
  if (!can("comments")) return;
  try {
    const s = await api("comments/stats");
    $("#nav-comments").textContent = s.needs;
    $("#nav-comments").hidden = !s.needs;
  } catch (e) { /* not linked yet */ }
}
