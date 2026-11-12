/* Staff portal front end. Plain JavaScript, no build step. Every value from the servers is escaped before it is shown. */
"use strict";

const S = { me: null, servers: [], timers: [], chatAfter: 0, page: "", templates: null, events: {} };
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
  $("#logout").onclick = async () => { await api("../auth/logout", {}).catch(() => {}); location.href = "/"; };
  $("#me-account").onclick = accountDialog;
  templates();
  $("#modal-cancel").onclick = closeModal;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
  window.addEventListener("hashchange", route);
  every(refreshReportCount, 30000);
  every(refreshAlertCount, 30000);
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

function accountDialog() {
  const me = S.me;
  const status = me.mfa_on ? '<p><span class="tag ok">On</span> Two-step sign-in protects this account.</p>'
    : `<p><span class="tag ${me.mfa_required ? "bad" : ""}">Off</span> ${me.mfa_required ? "Admin tools stay locked until you turn it on." : "Optional for moderators, and recommended."}</p>`;
  if (me.mfa_on) {
    return modal({ title: "Your account", sub: me.name + " · " + me.role, ok: me.mfa_required ? "Close" : "Turn off", danger: !me.mfa_required,
      body: status + (me.mfa_required ? "" : '<label>Code from your app, to turn it off</label><input name="code" inputmode="numeric" maxlength="7">'),
      onOk: async (f) => { if (me.mfa_required) return; await api("2fa/disable", { code: f.code }); toast("Two-step sign-in is off."); setTimeout(() => location.reload(), 800); } });
  }
  modal({ title: "Your account", sub: me.name + " · " + me.role, ok: "Set up two-step sign-in", body: status + '<p class="muted">You need an authenticator app such as Google Authenticator, Microsoft Authenticator, 1Password or Aegis.</p>',
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

function every(fn, ms, page) {
  fn();
  const id = setInterval(() => { if (!page || S.page === page) fn(); }, ms);
  if (page) S.timers.push(id);
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
  S.timers.forEach(clearInterval);
  S.timers = [];
  const parts = (location.hash || "#/servers").slice(2).split("/");
  const page = parts[0] || "servers";
  S.page = page + (parts[1] ? "/" + parts[1] : "");
  for (const a of document.querySelectorAll("#nav a")) a.classList.toggle("on", a.dataset.page === page || (page === "server" && a.dataset.page === "servers") || (page === "player" && a.dataset.page === "players"));
  const main = $("#main");
  main.innerHTML = '<p class="empty">Loading…</p>';
  const pages = { servers: pageServers, server: pageServer, chat: pageChat, reports: pageReports, players: pagePlayers,
    player: pagePlayer, bans: pageBans, audit: pageAudit, staff: pageStaff, health: pageHealth, alerts: pageAlerts,
    watchlist: pageWatchlist, review: pageReview, schedule: pageSchedule, filter: pageFilter, replies: pageReplies,
    weekly: pageWeekly, settings: pageSettings };
  let arg = "";
  try { arg = decodeURIComponent(parts[1] || ""); } catch (e) { arg = ""; }      // a broken link opens the page, not a blank screen
  (pages[page] || pageServers)(main, arg);
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
  }, 5000, "servers");
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
  every(() => drawServer(key), 3000, "server/" + key);
  every(() => pollChat(key), 2000, "server/" + key);
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
  every(() => pollChat(""), 2000, "chat");
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
      <label class="check"><input type="checkbox" name="ip_ban" checked> Also ban the IP address (uncheck for shared connections)</label>`,
    onOk: async (f) => {
      const r = await api("bans", Object.assign({ length: f.length, reason: f.reason, ip_ban: f.ip_ban }, target.pid ? { pid: target.pid } : { server: target.server, slot: target.slot, name: target.name }));
      const offline = Object.entries(r.servers).filter(([, v]) => v.startsWith("offline")).map(([k]) => k);
      toast("Banned " + target.name + (offline.length ? ". Offline now, applied at the next sync: " + offline.join(", ") : " on every server."), false, r.undo);
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
    const ap = e.target.closest("button[data-appeal]");
    if (ap) return appealDialog(+ap.dataset.appeal, ap.dataset.decision, ap.dataset.name, draw);
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
  every(draw, 20000, "reports");
}

function reportCard(r) {
  const d = r.data || {};
  const status = r.status === "open" ? '<span class="tag bad">Open</span>' : r.status === "claimed" ? `<span class="tag warn">${esc(r.claimed_by || "In progress")}</span>` : '<span class="tag ok">Closed</span>';
  const buttons = [r.status !== "claimed" && r.status !== "closed" ? `<button class="btn btn-small" data-id="${r.id}" data-do="claim">Take it</button>` : "",
    r.source === "appeal" ? "" : r.status !== "closed" ? `<button class="btn btn-small" data-id="${r.id}" data-do="close">Close</button>` : `<button class="btn btn-small" data-id="${r.id}" data-do="reopen">Reopen</button>`].join("");
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
    return `<div class="panel"><div class="head"><div><div class="tags">${status}<span class="tag">${esc(d.category || "Bug")}</span></div>
      <h2>${esc(d.summary || "Bug report")}</h2><span class="muted">Received ${when(r.received)}</span></div><div class="actions">${buttons}</div></div>
      <div class="report-body">${esc(d.text || "")}</div>${r.resolution ? `<p class="muted">Resolution: ${esc(r.resolution)}</p>` : ""}</div>`;
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

/* ------------------------------------------------------------------ players */
function pagePlayers(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Lookup</p><h1>Players</h1></div></div>
    <form class="search" id="lookup"><input name="q" placeholder="Name, player id${can("lookup.ip") ? " or IP address" : ""}" autocomplete="off"><button class="btn btn-primary">Search</button></form>
    <div class="panel" id="results"><p class="empty">Search by any name a player has used on our servers.</p></div>`;
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
      <td>${p.banned ? '<span class="tag bad">Banned</span>' : ""}</td></tr>`).join("")}</table>` : '<p class="empty">No player matches that.</p>';
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
      ${activeBan ? `<span class="tag bad">Banned · ${esc(until(activeBan.expires))}</span>` : ""}<span class="tag mono">${esc(pid)}</span></div></div>
    <div class="actions"><a class="btn" href="${esc(p.profile_url)}" target="_blank" rel="noopener">Public profile</a>
      ${can("watch") ? `<button class="btn" id="p-watch">${p.watch ? "Stop watching" : "Watch"}</button>` : ""}
      ${can("punish") && !activeBan ? '<button class="btn" id="p-punish">Punish</button>' : ""}
      ${can("ban.temp") && !activeBan ? '<button class="btn btn-danger" id="p-ban">Ban</button>' : ""}</div></div>
    ${p.watch ? `<div class="banner"><span>On the watchlist: ${esc(p.watch.reason || "no reason given")} · ${esc(p.watch.by_name)}, ${when(p.watch.created)}</span></div>` : ""}
    <div class="grid grid-2"><div>
      <div class="panel"><h3>Record</h3><ul class="list" id="p-record"></ul></div>
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
      <div class="panel"><h3>Staff notes</h3><ul class="list">${p.notes.map((n) => `<li>${esc(n.text)} <div class="dim">${esc(n.by_name)} · ${when(n.created)}</div></li>`).join("") || '<li class="dim">No notes yet.</li>'}</ul>
        <form id="p-note" class="chat-form"><input name="text" maxlength="1000" placeholder="Add a note for other staff"><button class="btn">Add</button></form></div>
    </div></div>`;
  const record = [];
  for (const b of p.bans) record.push([b.created, `<span class="tag bad">Ban</span> ${esc(b.reason)} <span class="dim">· ${esc(b.by_name)} · ${b.active ? esc(until(b.expires)) : "lifted" + (b.lifted_by ? " by " + esc(b.lifted_by) : "")}</span>`]);
  for (const m of p.mutes) record.push([m.created, `<span class="tag warn">Mute</span> ${esc(m.reason)} <span class="dim">· ${esc(m.by_name)}</span>`]);
  for (const w of p.warnings) record.push([w.created, `<span class="tag warn">Warning</span> ${esc(w.text)} <span class="dim">· ${esc(w.by_name)}</span>`]);
  for (const x of p.punishments || []) record.push([x.created, `<span class="tag staff">Ladder</span> ${esc((S.me.ladder[x.offence] || {}).label || x.offence)}: ${esc(x.step)} <span class="dim">· ${esc(x.by_name)}</span>`]);
  for (const x of p.appeals || []) record.push([x.created, `<span class="tag">Appeal</span> ${esc(x.status)}${x.answer ? ": " + esc(x.answer) : ""} <span class="dim">· ${esc(x.answered_by || "waiting")}</span>`]);
  for (const r of p.reports) record.push([r.received, `<span class="tag">${r.source === "auto" ? "Flag" : "Report"}</span> ${esc((r.data && r.data.reason) || "")} <span class="dim">· ${esc(r.status)}</span>`]);
  for (const a of p.actions.filter((x) => ["kick", "move", "unmute", "unban"].includes(x.action))) record.push([a.at, `<span class="tag">${esc(a.action)}</span> ${esc(a.detail)} <span class="dim">· ${esc(a.staff)}</span>`]);
  record.sort((a, b) => b[0] - a[0]);
  $("#p-record").innerHTML = record.map(([t, h]) => `<li>${h} <span class="dim">· ${when(t)}</span></li>`).join("") || '<li class="dim">Clean record.</li>';
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
    <div class="actions">${can("ban.remove") ? '<button class="btn" id="b-sync">Check every server now</button><button class="btn" id="b-server">Bans set in game</button>' : ""}</div></div>
    <div class="tabs" id="b-tabs"><button class="btn btn-small on" data-v="active">Active</button><button class="btn btn-small" data-v="all">History</button></div>
    <div class="panel table-wrap" id="b-list"></div><div id="b-extra"></div>`;
  $("#b-tabs").onclick = (e) => { const b = e.target.closest("button"); if (!b) return; for (const x of $("#b-tabs").children) x.classList.toggle("on", x === b); show = b.dataset.v; draw(); };
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
      <tr><td class="pname">${b.pid ? `<a href="#/player/${esc(b.pid)}">${esc(b.name)}</a>` : esc(b.name)}</td><td>${esc(b.reason)}</td><td>${esc(b.by_name)}</td><td>${when(b.created)}</td>
      <td>${b.active ? `<span class="tag bad">${esc(until(b.expires))}</span>` : `<span class="tag">Lifted${b.lifted_by ? " · " + esc(b.lifted_by) : ""}</span>`}</td>
      <td><div class="row-actions">${b.active && b.undo ? `<button class="btn btn-small" data-undo="${b.undo}">Undo</button>` : ""}${b.active && can("ban.remove") ? `<button class="btn btn-small" data-lift="${b.id}" data-name="${esc(b.name)}">Lift</button>` : ""}</div></td></tr>`).join("")}</table>` : '<p class="empty">No bans.</p>';
  }
  every(draw, 30000, "bans");
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
    <div class="actions"><button class="btn btn-primary" id="s-add">Add or change</button></div></div><div class="panel table-wrap" id="s-list"></div>`;
  const edit = (row = {}) => modal({ title: row.discord_id ? "Change " + (row.name || row.discord_id) : "Add staff", ok: "Save",
    sub: S.me.role === "owner" ? "" : "Only the owner can make or change admins.",
    body: `<label>Discord user id</label><input name="discord_id" value="${esc(row.discord_id || "")}" placeholder="183662139000000000" inputmode="numeric">
      <label>Name (for this list)</label><input name="name" value="${esc(row.name || "")}">
      <label>Access</label><select name="role"><option value="moderator">Moderator</option>${S.me.role === "owner" ? '<option value="admin">Admin</option>' : ""}<option value="discord">Follow Discord roles</option><option value="revoked">No access, even with the Discord role</option></select>
      <label>Note</label><input name="note" value="${esc(row.note || "")}" placeholder="Trial moderator until December">`,
    onOk: async (f) => { await api("staff", f); toast("Saved."); draw(); } });
  $("#s-add").onclick = () => edit();
  $("#s-list").onclick = (e) => { const b = e.target.closest("button[data-i]"); if (b) edit(draw.rows[+b.dataset.i]); };
  async function draw() {
    const r = await api("staff").catch((e) => { toast(e.message, true); return null; });
    if (!r) return;
    draw.rows = r.staff;
    $("#s-list").innerHTML = `<table><tr><th>Name</th><th>Discord id</th><th>Access</th><th>Last sign-in</th><th>Note</th><th></th></tr>${r.staff.map((s, i) => `
      <tr><td>${esc(s.name || "–")}</td><td class="mono">${esc(s.discord_id)}</td><td>${s.role ? `<span class="role">${esc(s.role)}</span>` : '<span class="dim">Discord role</span>'}</td>
      <td>${s.last_login ? ago(s.last_login) : "never"}</td><td>${esc(s.note || "")}</td><td>${s.role === "owner" ? "" : `<button class="btn btn-small" data-i="${i}">Change</button>`}</td></tr>`).join("")}</table>`;
  }
  draw();
}

/* ------------------------------------------------------------------ health */
function pageHealth(main) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow">Infrastructure</p><h1>Health</h1></div></div>
    <div class="cards" id="h-top"></div><div class="panel table-wrap" id="h-units"></div>`;
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
  every(draw, 15000, "alerts");
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

/* ------------------------------------------------------------------ settings (config editor) */
async function pageSettings(main, key) {
  main.innerHTML = `<div class="head"><div><p class="eyebrow"><a href="#/server/${esc(key)}">Server</a></p><h1>Settings</h1><p class="muted">Live server settings. "Keep" makes the portal put the value back after a restart or a config reload; without it the change lasts until the server restarts.</p></div></div>
    <div class="grid grid-2"><div class="panel table-wrap" id="cv-list"></div><div class="panel"><h3>History</h3><div id="cv-hist"></div></div></div>`;
  $("#cv-list").onclick = (e) => {
    const b = e.target.closest("button[data-i]"); if (!b) return;
    const c = draw.rows[+b.dataset.i];
    if (b.dataset.do === "release") return api("cvars/release", { server: key, cvar: c.name }).then(() => { toast("No longer kept."); draw(); }).catch((err) => toast(err.message, true));
    modal({ title: c.label, sub: c.name + " · now " + (c.value ?? "unknown"), ok: "Apply",
      body: `<label>New value</label><input name="value" maxlength="64" value="${esc(c.kept ?? c.value ?? "")}" pattern="[A-Za-z0-9 ._-]*">
        <label class="check"><input type="checkbox" name="keep"${c.kept != null ? " checked" : ""}> Keep after restarts</label>`,
      onOk: async (f) => { const r = await api("cvars", { server: key, cvar: c.name, value: f.value, keep: f.keep }); toast(r.note || c.name + " is now " + r.value + "."); draw(); } });
  };
  $("#cv-hist").onclick = (e) => {
    const b = e.target.closest("button[data-rb]"); if (!b) return;
    api("cvars/rollback", { id: +b.dataset.rb }).then((r) => { toast("Rolled back to " + r.value + "."); draw(); }).catch((err) => toast(err.message, true));
  };
  async function draw() {
    let r;
    try { r = await api("cvars?server=" + encodeURIComponent(key)); } catch (e) { $("#cv-list").innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
    draw.rows = r.cvars;
    $("#cv-list").innerHTML = `<table><tr><th>Setting</th><th>Value</th><th></th></tr>${r.cvars.map((c, i) => `
      <tr><td>${esc(c.label)}<div class="cvar-name">${esc(c.name)}</div></td>
      <td class="mono">${c.value == null ? `<span class="dim">${r.offline ? "server not answering" : "not on this server"}</span>` : esc(c.value)}${c.kept != null ? ' <span class="kept" title="Kept after restarts">kept</span>' : ""}${c.event ? ' <span class="tag">event</span>' : ""}</td>
      <td><div class="row-actions">${c.value != null && !c.event ? `<button class="btn btn-small" data-i="${i}">Change</button>` : ""}${c.kept != null ? `<button class="btn btn-small" data-i="${i}" data-do="release">Stop keeping</button>` : ""}</div></td></tr>`).join("")}</table>`;
    $("#cv-hist").innerHTML = r.history.length ? `<ul class="list">${r.history.map((h) => `<li><span class="mono">${esc(h.cvar)}</span> ${esc(h.old)} → <b>${esc(h.new)}</b>
      <div class="dim small">${esc(h.kind)}${h.kept ? ", kept" : ""} · ${esc(h.by_name)} · ${when(h.at)}</div>
      ${["set", "rollback"].includes(h.kind) ? `<button class="btn btn-small" data-rb="${h.id}">Roll back to ${esc(h.old)}</button>` : ""}</li>`).join("")}</ul>` : '<p class="empty">No changes yet.</p>';
  }
  draw();
}

boot();
