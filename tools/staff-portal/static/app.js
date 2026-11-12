/* Staff portal front end. Plain JavaScript, no build step. Every value from the servers is escaped before it is shown. */
"use strict";

const S = { me: null, servers: [], timers: [], chatAfter: 0, page: "" };
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

function toast(msg, bad) {
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast" + (bad ? " bad" : "");
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { t.hidden = true; }, bad ? 7000 : 3500);
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
  m.hidden = false;
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
  $("#app").hidden = false;
  $("#me-name").textContent = me.name;
  $("#me-role").textContent = me.role;
  if (me.avatar) { $("#me-avatar").src = me.avatar; $("#me-avatar").hidden = false; }
  for (const a of document.querySelectorAll("#nav a[data-perm]")) a.hidden = !can(a.dataset.perm);
  $("#logout").onclick = async () => { await api("../auth/logout", {}).catch(() => {}); location.href = "/"; };
  $("#modal-cancel").onclick = closeModal;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });
  window.addEventListener("hashchange", route);
  every(refreshReportCount, 30000);
  route();
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
    player: pagePlayer, bans: pageBans, audit: pageAudit, staff: pageStaff, health: pageHealth };
  (pages[page] || pageServers)(main, decodeURIComponent(parts[1] || ""));
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
    <div class="grid grid-2">
      <div><div class="panel"><div class="table-wrap"><table id="players"></table></div></div>
        <div class="panel"><h3>Server control</h3><div id="controls" class="tags"></div></div></div>
      <div class="panel chat"><h3>Chat</h3><div class="chat-log" id="chat-log"></div>
        ${can("chat.reply") ? '<form class="chat-form" id="chat-form"><input name="text" maxlength="200" placeholder="Reply as staff" autocomplete="off"><button class="btn btn-primary">Send</button></form>' : ""}</div>
    </div>`;
  S.chatAfter = 0;
  const controls = [];
  if (can("server.say")) controls.push('<button class="btn btn-small" data-c="say">Announce</button>');
  if (can("server.map")) controls.push('<button class="btn btn-small" data-c="map">Change map now</button>', '<button class="btn btn-small" data-c="nextmap">Skip to next map</button>', '<button class="btn btn-small" data-c="rotation">Edit rotation</button>');
  if (can("server.restart")) controls.push('<button class="btn btn-small btn-danger" data-c="restart">Restart match</button>');
  $("#controls").innerHTML = controls.join("") || '<span class="dim">Your role has no server controls.</span>';
  $("#controls").onclick = (e) => { const c = e.target.dataset.c; if (c) serverControl(key, c); };
  const form = $("#chat-form");
  if (form) form.onsubmit = async (e) => {
    e.preventDefault();
    const text = form.text.value.trim();
    if (!text) return;
    try { await api("server", { server: key, action: "chat", text }); form.text.value = ""; pollChat(key); } catch (err) { toast(err.message, true); }
  };
  $("#players").onclick = (e) => { const b = e.target.closest("button[data-a]"); if (b) playerAction(key, +b.dataset.slot, b.dataset.name, b.dataset.a); };
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
  const head = `<tr><th>Player</th><th>Team</th><th class="num">Score</th>${extra ? '<th class="num">K/D</th>' : ""}<th class="num">Ping</th><th>Anti-cheat</th><th class="num">Time</th><th></th></tr>`;
  const body = rows.map((p) => {
    const flags = [];
    if (p.bot) flags.push('<span class="tag">Bot</span>');
    if (p.open_reports) flags.push(`<span class="tag bad" title="Open reports">${p.open_reports} report${p.open_reports > 1 ? "s" : ""}</span>`);
    if (p.warnings) flags.push(`<span class="tag warn" title="Warnings">${p.warnings} warn</span>`);
    if (p.past_bans) flags.push(`<span class="tag bad" title="Earlier bans">${p.past_bans} ban${p.past_bans > 1 ? "s" : ""}</span>`);
    if (p.muted_s || p.mute_until !== undefined) flags.push('<span class="tag warn">Muted</span>');
    if (p.detections) flags.push(`<span class="tag bad">${p.detections} detections</span>`);
    const name = p.pid ? `<a href="#/player/${esc(p.pid)}">${esc(p.name)}</a>` : esc(p.name);
    const team = p.spectator ? "Spectator" : p.team != null ? TEAM[p.team] || "–" : "–";
    const eac = p.bot ? '<span class="dim">–</span>' : p.eac === "protected" ? '<span class="tag ok">Protected</span>' : p.eac ? `<span class="tag warn">${esc(p.eac)}</span>` : '<span class="dim">–</span>';
    const btn = (a, label, perm, danger) => can(perm) ? `<button class="btn btn-small${danger ? " btn-danger" : ""}" data-a="${a}" data-slot="${p.slot}" data-name="${esc(p.name)}">${label}</button>` : "";
    const actions = [btn("warn", "Warn", "player.warn"), btn(p.muted_s ? "unmute" : "mute", p.muted_s ? "Unmute" : "Mute", "player.mute"),
      btn("move", "Move", "player.move"), btn("kick", "Kick", "player.kick", true), p.bot ? "" : btn("ban", "Ban", "ban.temp", true)].join("");
    return `<tr class="team-${p.spectator ? 0 : p.team || 0}"><td class="pname">${name}<span class="flags">${flags.join("")}</span></td>
      <td>${esc(team)}</td><td class="num">${p.score}</td>${extra ? `<td class="num">${p.kills ?? "–"}/${p.deaths ?? "–"}</td>` : ""}
      <td class="num">${p.ping < 0 ? esc(p.state) : p.ping}</td><td>${eac}</td><td class="num">${dur(p.connected_s)}</td>
      <td><div class="row-actions">${actions}</div></td></tr>`;
  }).join("");
  $("#players").innerHTML = head + (body || `<tr><td colspan="8" class="empty">Nobody is on this server.</td></tr>`);
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
    div.className = "chat-line " + (l.kind || "");
    const srv = showServer ? `<span class="srv">${esc(l.server)}</span>` : "";
    const who = l.pid ? `<a class="who" href="#/player/${esc(l.pid)}">${esc(l.name)}:</a>` : `<span class="who">${esc(l.name)}:</span>`;
    div.innerHTML = `<time>${clock(l.at)}</time>${srv}${who} ${esc(l.text)}`;
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

function playerAction(server, slot, name, a) {
  const base = { server, slot, name };
  const send = (extra, label) => async () => {
    const r = await api("action", Object.assign({ action: a }, base, extra));
    toast(label + (r.result ? " · " + r.result.split("\n")[0] : ""));
    drawServer(server);
  };
  if (a === "kick") return modal({ title: "Kick " + name, sub: "The player sees the reason and can reconnect.", ok: "Kick", danger: true,
    body: '<label>Reason</label><input name="reason" maxlength="100" required placeholder="Team killing">',
    onOk: (f) => send({ reason: f.reason }, "Kicked " + name)() });
  if (a === "warn") return modal({ title: "Warn " + name, sub: "Only this player sees the warning. It is kept on their record.", ok: "Send warning",
    body: '<label>Warning</label><input name="reason" maxlength="100" placeholder="Stop spawn camping. Next time it is a kick.">',
    onOk: (f) => send({ reason: f.reason }, "Warned " + name)() });
  if (a === "mute") return modal({ title: "Mute " + name, sub: "Blocks text and voice commands. The mute follows the player across maps and servers.", ok: "Mute",
    body: `<label>Length</label><select name="length">${LENGTHS.filter((l) => l[0] !== "30d").map((l) => `<option value="${l[0]}">${l[1]}</option>`).join("").replace("Permanent", "Until lifted")}</select>
      <label>Reason</label><input name="reason" maxlength="100" placeholder="Spamming chat">`,
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
      <label>Reason</label><input name="reason" maxlength="100" placeholder="Cheating (aimbot), see report #12">
      <label class="check"><input type="checkbox" name="ip_ban" checked> Also ban the IP address (uncheck for shared connections)</label>`,
    onOk: async (f) => {
      const r = await api("bans", Object.assign({ length: f.length, reason: f.reason, ip_ban: f.ip_ban }, target.pid ? { pid: target.pid } : { server: target.server, slot: target.slot, name: target.name }));
      const offline = Object.entries(r.servers).filter(([, v]) => v.startsWith("offline")).map(([k]) => k);
      toast("Banned " + target.name + (offline.length ? ". Offline now, applied at the next sync: " + offline.join(", ") : " on every server."));
      if (target.server) drawServer(target.server); else route();
    } });
}

function sayDialog(server) {
  modal({ title: server === "*" ? "Message every server" : "Announce", sub: "Shown in chat to everyone, marked as staff.", ok: "Send",
    body: '<label>Message</label><input name="text" maxlength="200" placeholder="The server restarts for an update in 5 minutes.">',
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
    <div class="tabs" id="r-source"><button class="btn btn-small on" data-k="">Everything</button><button class="btn btn-small" data-k="player">Player reports</button><button class="btn btn-small" data-k="auto">Automatic flags</button><button class="btn btn-small" data-k="bug">Bug reports</button></div>
    <div id="r-list"></div>`;
  const tabs = (id, attr, key) => $(id).onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    for (const x of $(id).children) x.classList.toggle("on", x === b);
    state[key] = b.dataset[attr]; draw();
  };
  tabs("#r-status", "s", "status");
  tabs("#r-source", "k", "source");
  $("#r-list").onclick = async (e) => {
    const b = e.target.closest("button[data-id]"); if (!b) return;
    const set = async (status, resolution) => { await api("reports/update", { id: +b.dataset.id, status, resolution }); toast("Report updated."); draw(); refreshReportCount(); };
    if (b.dataset.do === "close") modal({ title: "Close report", ok: "Close", body: '<label>What was done</label><input name="r" maxlength="200" placeholder="Watched the demo, banned 7 days">', onOk: (f) => set("closed", f.r) });
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
    r.status !== "closed" ? `<button class="btn btn-small" data-id="${r.id}" data-do="close">Close</button>` : `<button class="btn btn-small" data-id="${r.id}" data-do="reopen">Reopen</button>`].join("");
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
      ${can("ban.temp") && !activeBan ? '<button class="btn btn-danger" id="p-ban">Ban</button>' : ""}</div></div>
    <div class="grid grid-2"><div>
      <div class="panel"><h3>Record</h3><ul class="list" id="p-record"></ul></div>
      <div class="panel"><h3>Recent matches</h3><div class="table-wrap">${p.matches.length ? `<table><tr><th>Ended</th><th>Map</th><th class="num">K</th><th class="num">D</th><th class="num">HS</th><th>Result</th></tr>${p.matches.map((m) => `<tr><td>${esc(String(m.ended || "").replace("T", " ").slice(0, 16))}</td><td>${esc(m.map)}</td><td class="num">${m.kills}</td><td class="num">${m.deaths}</td><td class="num">${m.headshots}</td><td>${m.won ? "Won" : "Lost"}</td></tr>`).join("")}</table>` : '<p class="empty">No stats-tracked matches yet.</p>'}</div></div>
      <div class="panel"><h3>Recent chat</h3><div class="chat-log" id="p-chat"></div></div>
    </div><div>
      <div class="panel"><h3>Identity</h3><dl class="kv">
        <dt>First seen</dt><dd>${p.first_seen ? when(p.first_seen) : "–"}</dd><dt>Last seen</dt><dd>${p.last_seen ? ago(p.last_seen) : "–"}</dd>
        <dt>Servers</dt><dd>${esc(p.servers.join(", ") || "–")}</dd>
        <dt>Anti-cheat id</dt><dd class="mono">${esc(p.puids.join(", ") || "–")}</dd>
        ${st ? `<dt>Rating</dt><dd>${st.ranked ? esc(st.rating) + (st.position ? " · #" + esc(st.position) : "") : "not ranked yet"} · ${esc(st.matches)} matches</dd><dt>Career</dt><dd>${esc(st.kills)} K · ${esc(st.deaths)} D · ${esc(st.teamKills ?? 0)} TK</dd>` : ""}
      </dl></div>
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
      <td>${b.active && can("ban.remove") ? `<button class="btn btn-small" data-lift="${b.id}" data-name="${esc(b.name)}">Lift</button>` : ""}</td></tr>`).join("")}</table>` : '<p class="empty">No bans.</p>';
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

boot();
