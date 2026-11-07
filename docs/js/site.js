/* TrueCombat: Platinum website: shared script for every page (English and Dutch).
   Sections opt in with data attributes:
     [data-download]              download buttons, pointed at the newest full zip
     [data-releases="5"|"all"]    patch notes from GitHub Releases (static HTML stays as fallback)
     [data-servers="5"|"all"]     live server list from the bridge (tools/server-bridge)
     [data-leaderboard]           leaderboards from the bridge (rows link to player.html?id=)
     [data-player]                player profile page (player.html?id=<player id>)
     [data-gallery]               screenshot grid with filter tabs and a lightbox (media page)
     [data-yt]                    click-to-play YouTube embed (privacy-enhanced, nothing loads before a click)
   Set TCP_API to the bridge's public https URL once it is hosted. Empty means "offline". */
var TCP_API = 'https://api.truecombat.eu';

(function () {
  var lang = (document.documentElement.lang || 'en').slice(0, 2);
  var DICT = {
    en: {
      months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
      latest: 'Latest', offline: 'Master server offline', online: 'Online', loading: 'Checking…',
      noServersOffline: 'No public servers yet. This list fills in automatically when the master server is running.',
      noServers: 'Nobody is hosting a public server right now. Host one from the launcher with List publicly switched on.',
      players: 'players', servers: 'servers', password: 'Password', copy: 'Copy address', copied: 'Copied',
      updated: 'Updated', join: 'In the launcher: Servers → Join by address',
      lbEmpty: 'No ranked matches yet. Leaderboards fill in once public servers report their matches.',
      lbOffline: 'The leaderboards are temporarily unavailable. Please check back in a few minutes.',
      soon: 'Coming soon', matches: 'matches', rating: 'Rating', peak: 'Peak', kd: 'K/D', headshots: 'Headshots', wins: 'Wins', played: 'Played', accuracy: 'Accuracy',
      xpTo: 'XP to', topRank: 'Highest rank reached', weapons: 'Weapons', recent: 'Recent matches', close: 'Close', notRanked: 'Not ranked yet: finish three matches.',
      position: 'Position', noPlayer: 'No player found with that name.', unknownPlayer: 'This player has no recorded matches yet.', won: 'Win', lost: 'Loss', hours: 'h', minutes: 'min',
      play: 'Play the trailer', notesFailed: 'GitHub could not be reached. Showing the notes built into this page.',
      kills: 'Kills', deaths: 'Deaths', winRate: 'Win rate', damage: 'Damage', objectives: 'Objectives', roundsWon: 'Rounds won', teamKills: 'Team kills',
      profile: 'Player profile', firstSeen: 'First seen', lastSeen: 'Last seen', copyLink: 'Copy profile link', linkCopied: 'Link copied',
      trendShort: 'Rating history appears after two rated matches.', lastN: 'Last {n} matches', found: '{n} found',
      apiOffline: 'Player stats are offline right now. Please try again in a few minutes.', screenshots: 'screenshots'
    },
    nl: {
      months: ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'],
      latest: 'Nieuwste', offline: 'Masterserver offline', online: 'Online', loading: 'Bezig…',
      noServersOffline: 'Nog geen publieke servers. Deze lijst vult zich vanzelf zodra de masterserver draait.',
      noServers: 'Er host nu niemand een publieke server. Host er zelf een vanuit de launcher met Openbaar tonen aan.',
      players: 'spelers', servers: 'servers', password: 'Wachtwoord', copy: 'Adres kopiëren', copied: 'Gekopieerd',
      updated: 'Bijgewerkt', join: 'In de launcher: Servers → Verbinden met adres',
      lbEmpty: 'Nog geen gerankte potjes. De ranglijsten vullen zich zodra publieke servers hun potjes doorgeven.',
      lbOffline: 'De ranglijsten zijn tijdelijk niet beschikbaar. Probeer het over een paar minuten opnieuw.',
      soon: 'Binnenkort', matches: 'potjes', rating: 'Rating', peak: 'Hoogste', kd: 'K/D', headshots: 'Headshots', wins: 'Winst', played: 'Gespeeld', accuracy: 'Trefzekerheid',
      xpTo: 'XP tot', topRank: 'Hoogste rang bereikt', weapons: 'Wapens', recent: 'Laatste potjes', close: 'Sluiten', notRanked: 'Nog niet gerankt: speel drie potjes uit.',
      position: 'Positie', noPlayer: 'Geen speler met die naam gevonden.', unknownPlayer: 'Van deze speler zijn nog geen potjes bekend.', won: 'Winst', lost: 'Verlies', hours: 'u', minutes: 'min',
      play: 'Speel de trailer af', notesFailed: 'GitHub was niet bereikbaar. Je ziet de notities die in deze pagina zitten.',
      kills: 'Kills', deaths: 'Doden', winRate: 'Winstpercentage', damage: 'Schade', objectives: 'Doelen', roundsWon: 'Rondes gewonnen', teamKills: 'Teamkills',
      profile: 'Spelersprofiel', firstSeen: 'Eerst gezien', lastSeen: 'Laatst gezien', copyLink: 'Profiellink kopiëren', linkCopied: 'Link gekopieerd',
      trendShort: 'Het ratingverloop verschijnt na twee gerankte potjes.', lastN: 'Laatste {n} potjes', found: '{n} gevonden',
      apiOffline: 'De spelersstatistieken zijn nu offline. Probeer het over een paar minuten opnieuw.', screenshots: 'screenshots'
    }
  };
  var L = DICT[lang] || DICT.en;

  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtDate(iso) { var d = new Date(iso); return d.getUTCDate() + ' ' + L.months[d.getUTCMonth()] + ' ' + d.getUTCFullYear(); }
  function inline(t) { return esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>'); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  var CHEV = ' <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';

  /* mobile menu closes after a pick */
  var menu = document.getElementById('menu');
  if (menu) menu.addEventListener('click', function (e) { if (e.target.tagName === 'A') menu.open = false; });

  /* ---------- GitHub releases ---------- */
  var RELEASES = 'https://api.github.com/repos/Annoximeme/TrueCombat-Platinum/releases?per_page=30';
  function getReleases(cb) {
    var cached = null;
    try { cached = JSON.parse(sessionStorage.getItem('tcp-releases2') || 'null'); } catch (e) {}
    if (cached && Date.now() - cached.t < 30 * 60 * 1000) { cb(cached.data); return; }
    fetch(RELEASES, { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (list) {
        var slim = list.filter(function (r) { return !r.draft && !r.prerelease; }).map(function (r) {
          return { tag_name: r.tag_name, name: r.name, html_url: r.html_url, published_at: r.published_at, body: r.body,
            assets: (r.assets || []).map(function (a) { return { name: a.name, size: a.size, browser_download_url: a.browser_download_url }; }) };
        });
        try { sessionStorage.setItem('tcp-releases2', JSON.stringify({ t: Date.now(), data: slim })); } catch (e) {}
        cb(slim);
      })
      .catch(function () { cb(null); });
  }
  /* same headings as tools/website/release_sync.py */
  var TITLES = { 'HUD': 'HUD', 'UI': 'UI', 'DX12': 'DirectX 12', 'DIRECTX 12': 'DirectX 12', 'STATUS': 'Known issues', 'KNOWN ISSUES': 'Known issues', 'FIXES': 'Fixes', 'BUG FIXES': 'Fixes' };
  function sectionTitle(t) { var u = t.toUpperCase(); return TITLES[u] || (t.charAt(0).toUpperCase() + t.slice(1).toLowerCase()); }
  function parseNotes(body) {
    var lines = (body || '').replace(/\r/g, '').split('\n');
    var out = { num: '', build: '', summary: '', sections: [] }, sec = null;
    lines.forEach(function (raw) {
      var l = raw.trim(); if (!l) return;
      var h = /^\*\*([^*]+)\*\*\s*(.*)$/.exec(l);
      if (h && !h[2]) {
        var t = h[1].trim();
        var num = /Patch Notes\s*#(\d+)/i.exec(t);
        if (num) { out.num = num[1]; return; }
        if (/^TRUECOMBAT/i.test(t)) return;
        sec = { title: sectionTitle(t), items: [] };
        if (!/^development$/i.test(t)) out.sections.push(sec);
        return;
      }
      if (h && /Packaged Native Sandbox/i.test(h[1])) { out.build = h[2].trim(); return; }
      if (h) return;
      if (/^[-*]\s+/.test(l)) { if (sec) sec.items.push(l.replace(/^[-*]\s+/, '')); return; }
      if (!sec && !out.summary) {
        var sm = l.replace(/^New download for the native 64-bit sandbox[.,]?\s*(with\s+)?/i, '');
        out.summary = sm.charAt(0).toUpperCase() + sm.slice(1);
      }
    });
    return out;
  }
  function verOf(rel) { var m = /^v?(\d+\.\d+\.\d+)/.exec(rel.tag_name || ''); return m ? 'v' + m[1] : rel.tag_name; }
  function releaseHTML(rel, first, withLink) {
    var n = parseNotes(rel.body);
    if (!n.sections.length) return '';
    var ver = esc(verOf(rel));
    var meta = (n.num ? '#' + n.num + ' · ' : '') + esc(n.build || rel.tag_name) + ' · ' + fmtDate(rel.published_at);
    var secs = n.sections.map(function (sec) {
      return '<section><h3>' + esc(sec.title) + '</h3><ul>' + sec.items.map(function (it) { return '<li>' + inline(it) + '</li>'; }).join('') + '</ul></section>';
    }).join('');
    var link = withLink && rel.html_url ? '<p class="rel-link"><a href="' + esc(rel.html_url) + '">GitHub ↗</a></p>' : '';
    return '<details class="release" id="' + ver + '" data-ver="' + ver + '"' + (first ? ' open' : '') + '><summary><span class="ver">' + ver +
      (first ? '<span class="latest">' + L.latest + '</span>' : '') + '</span><span class="sum">' + inline(n.summary) +
      '</span><span class="meta">' + meta + CHEV + '</span></summary><div class="body">' + secs + link + '</div></details>';
  }
  function renderNotes(box, rels) {
    var limit = box.dataset.releases === 'all' ? 999 : parseInt(box.dataset.releases, 10) || 5;
    var seen = {};
    var html = rels.slice(0, limit).map(function (rel, i) { seen[verOf(rel)] = true; return releaseHTML(rel, i === 0, limit > 5); }).join('');
    if (!html) return;
    /* keep hand-written entries for versions the API does not return */
    var older = $all('.release[data-ver]', box).filter(function (d) { return !seen[d.dataset.ver]; });
    older.forEach(function (d) { d.open = false; var b = d.querySelector('.latest'); if (b) b.remove(); });
    box.innerHTML = html;
    older.slice(0, Math.max(0, limit - Object.keys(seen).length)).forEach(function (d) { box.appendChild(d); });
    if (location.hash) { var t = document.getElementById(location.hash.slice(1)); if (t && t.tagName === 'DETAILS') { t.open = true; t.scrollIntoView(); } }
  }
  function applyDownload(rels) {
    $all('[data-version]').forEach(function (el) { el.textContent = verOf(rels[0]); });
    for (var i = 0; i < rels.length; i++) {
      var zip = (rels[i].assets || []).filter(function (a) { return /Windows-x64\.zip$/i.test(a.name); })[0];
      if (!zip) continue;
      var mb = Math.round(zip.size / 1048576).toLocaleString(lang) + ' MB';
      $all('[data-size]').forEach(function (el) { el.textContent = mb; });
      $all('[data-date]').forEach(function (el) { el.textContent = fmtDate(rels[i].published_at); });
      $all('[data-download]').forEach(function (el) { el.href = zip.browser_download_url; });
      return;
    }
  }
  var noteBoxes = $all('[data-releases]');
  if (noteBoxes.length || document.querySelector('[data-download]')) {
    getReleases(function (rels) {
      if (!rels || !rels.length) {
        $all('[data-releases-status]').forEach(function (el) { el.textContent = L.notesFailed; el.hidden = false; });
        return;
      }
      noteBoxes.forEach(function (box) { renderNotes(box, rels); });
      applyDownload(rels);
    });
  }

  /* ---------- live servers (bridge JSON, see tools/server-bridge) ---------- */
  var MAPS = { obj_delta: 'Delta', obj_northport: 'Northport', obj_railhouse: 'Railhouse', obj_snow: 'Snow', obj_stadtrand: 'Stadtrand', obj_village: 'Village' };
  function mapLabel(m) {
    var key = String(m || '').toLowerCase();
    var name = MAPS[key];
    return name ? '<a href="maps.html#' + name.toLowerCase() + '">' + name + '</a>' : esc(m);
  }
  function api(path) {
    if (!TCP_API) return Promise.reject(new Error('offline'));
    return fetch(TCP_API.replace(/\/$/, '') + path, { cache: 'no-store' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  function setPill(root, ok, text) {
    var pill = root.querySelector('.pill');
    if (pill) { pill.textContent = text; pill.classList.toggle('ok', ok); }
  }
  function renderServers(root, data) {
    var limit = root.dataset.servers === 'all' ? 999 : parseInt(root.dataset.servers, 10) || 5;
    var list = (data.servers || []).slice().sort(function (a, b) { return (b.players || 0) - (a.players || 0); });
    var tbody = root.querySelector('tbody');
    var empty = root.querySelector('.srv-empty');
    var total = list.reduce(function (s, x) { return s + (x.players || 0); }, 0);
    setPill(root, true, list.length + ' ' + L.servers + ' · ' + total + ' ' + L.players);
    if (!list.length) { if (empty) empty.textContent = L.noServers; return; }
    if (empty) empty.hidden = true;
    tbody.innerHTML = list.slice(0, limit).map(function (s) {
      return '<tr><td><b>' + esc(s.name) + '</b>' + (s.password ? ' <span class="lock" title="' + L.password + '">🔒</span>' : '') +
        '<button type="button" class="addr" data-addr="' + esc(s.address) + '" title="' + L.copy + '">' + esc(s.address) + '</button></td>' +
        '<td>' + mapLabel(s.map) + '</td><td>' + (s.players || 0) + ' / ' + (s.maxPlayers || '?') + '</td><td>' + esc(s.mode || '') + '</td></tr>';
    }).join('');
    var upd = root.querySelector('.srv-updated');
    if (upd && data.updated) { upd.textContent = L.updated + ' ' + new Date(data.updated).toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' }); upd.hidden = false; }
  }
  $all('[data-servers]').forEach(function (root) {
    root.addEventListener('click', function (e) {
      var b = e.target.closest('.addr'); if (!b) return;
      var a = b.dataset.addr;
      (navigator.clipboard ? navigator.clipboard.writeText(a) : Promise.reject()).then(function () {
        b.textContent = L.copied; setTimeout(function () { b.textContent = a; }, 1400);
      }, function () {});
    });
    function load() {
      api('/servers.json').then(function (d) { renderServers(root, d); }, function () {
        setPill(root, false, L.offline);
        var empty = root.querySelector('.srv-empty'); if (empty) empty.textContent = L.noServersOffline;
      });
    }
    load();
    if (TCP_API) setInterval(function () { if (!document.hidden) load(); }, 60000);
  });

  /* ---------- leaderboards and player profiles (stats service JSON, tools/server-bridge/tcp_stats.py) ---------- */
  function num(n) { return (n || 0).toLocaleString(lang); }
  function pct(n) { return Math.round((n || 0) * 100) + '%'; }
  function badge(r) { return r ? '<span class="badge" title="' + esc(r.title) + '">' + esc(r.short) + '</span>' : ''; }
  function dur(s) { var h = Math.floor((s || 0) / 3600), m = Math.round(((s || 0) % 3600) / 60); return h ? h + ' ' + L.hours + ' ' + m + ' ' + L.minutes : m + ' ' + L.minutes; }
  function kdOf(p) { return p.deaths ? p.kills / p.deaths : (p.kills || 0); }
  function profileHref(id) { return 'player.html?id=' + encodeURIComponent(id); }
  var PID = /^[0-9a-f]{16}$/;

  $all('[data-leaderboard]').forEach(function (root) {
    var tbody = root.querySelector('tbody');
    var empty = root.querySelector('.lb-empty');
    var search = root.querySelector('[data-lb-search]');
    var state = { period: 'all', sort: 'rating', data: {}, found: null };
    function prep(p) { p.kd = kdOf(p); p.hs = p.kills ? p.headshots / p.kills : 0; p.xp = p.rank ? p.rank.xp : 0; return p; }
    function row(p, i) {
      return '<tr><td class="rank">' + (i + 1) + '</td><td><a class="who" href="' + esc(profileHref(p.id)) + '">' + esc(p.name) + '</a></td>' +
        '<td>' + badge(p.rank) + '</td><td>' + num(p.rating) + '</td><td>' + num(p.matches) + '</td><td>' + num(p.kills) +
        '</td><td>' + p.kd.toFixed(2) + '</td><td>' + pct(p.hs) + '</td><td>' + num(p.wins) + '</td><td>' + esc(p.topWeapon || '–') + '</td></tr>';
    }
    function draw() {
      var d = state.data[state.period];
      if (!d) return;
      var rows = (state.found || d.players || []).slice().map(prep);
      rows.sort(function (a, b) { return (b[state.sort] || 0) - (a[state.sort] || 0) || (b.kills || 0) - (a.kills || 0); });
      setPill(root, true, num(d.matches) + ' ' + L.matches);
      if (!rows.length) { empty.textContent = state.found ? L.noPlayer : L.lbEmpty; empty.hidden = false; tbody.innerHTML = ''; return; }
      empty.hidden = true;
      tbody.innerHTML = rows.slice(0, 100).map(row).join('');
    }
    function load() {
      if (state.data[state.period]) { draw(); return; }
      api('/leaderboard.json?limit=500&period=' + state.period).then(function (d) { state.data[state.period] = d; draw(); }, function () {
        setPill(root, false, TCP_API ? L.offline : L.soon); empty.textContent = L.lbOffline; empty.hidden = false;
      });
    }
    /* old links: leaderboards.html#player=<id> now open the profile page */
    var old = /player=([0-9a-f]{16})/.exec(location.hash);
    if (old) location.replace(profileHref(old[1]));
    if (search && !TCP_API) search.hidden = true;
    if (search && TCP_API) {
      var timer = null;
      function find() {
        var q = search.q.value.trim();
        if (q.length < 2) { state.found = null; draw(); return; }
        api('/search.json?q=' + encodeURIComponent(q)).then(function (d) { state.found = d.players || []; draw(); }, function () {});
      }
      search.addEventListener('submit', function (e) { e.preventDefault(); find(); });
      search.q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(find, 300); });
    }
    $all('[data-period]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        $all('[data-period]', root).forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
        state.period = b.dataset.period; load();
      });
    });
    $all('[data-sort]', root).forEach(function (b) {
      b.addEventListener('click', function () {
        $all('[data-sort]', root).forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
        state.sort = b.dataset.sort; draw();
      });
    });
    load();
  });

  /* ---------- player profile page ---------- */
  $all('[data-player]').forEach(function (root) {
    function q(sel) { return root.querySelector(sel); }
    var id = (new URLSearchParams(location.search).get('id') || '').toLowerCase();
    var search = q('[data-pf-search]');
    var results = q('[data-pf-results]');

    function showSearch(players) {
      var tb = results.querySelector('tbody'), empty = results.querySelector('.srv-empty');
      q('[data-pf-count]').textContent = L.found.replace('{n}', players.length);
      tb.innerHTML = players.map(function (p) {
        return '<tr><td><a class="who" href="' + esc(profileHref(p.id)) + '">' + esc(p.name) + '</a></td><td>' + badge(p.rank) + '</td><td>' + num(p.rating) +
          '</td><td>' + num(p.matches) + '</td><td>' + num(p.kills) + '</td><td>' + kdOf(p).toFixed(2) + '</td></tr>';
      }).join('');
      empty.hidden = players.length > 0;
      results.hidden = false;
    }
    if (search) {
      if (!TCP_API) search.hidden = true;
      var timer = null;
      var find = function () {
        var term = search.q.value.trim();
        if (term.length < 2) { results.hidden = true; return; }
        api('/search.json?q=' + encodeURIComponent(term)).then(function (d) { showSearch(d.players || []); }, function () {});
      };
      search.addEventListener('submit', function (e) { e.preventDefault(); find(); });
      search.q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(find, 300); });
    }

    function missing(text) { var m = q('[data-pf-missing]'); q('[data-pf-missing-text]').textContent = text; m.hidden = false; }
    if (!id) return;
    if (!PID.test(id)) { missing(L.unknownPlayer); return; }
    if (!TCP_API) { missing(L.apiOffline); return; }

    function chart(p) {
      var rec = (p.recent || []).slice().reverse();
      var box = q('[data-pf-chart]');
      if (rec.length < 2) { box.innerHTML = '<p class="muted">' + L.trendShort + '</p>'; q('[data-pf-trend-note]').hidden = true; return; }
      q('[data-pf-trend-note]').textContent = L.lastN.replace('{n}', rec.length);
      var total = rec.reduce(function (s, m) { return s + (m.ratingChange || 0); }, 0);
      var r = p.rating - total, pts = [r];
      rec.forEach(function (m) { r += m.ratingChange || 0; pts.push(r); });
      var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts);
      if (hi - lo < 20) { var mid = (hi + lo) / 2; lo = mid - 10; hi = mid + 10; }
      var W = 640, H = 180, P = 14;
      function x(i) { return P + i * (W - 2 * P) / (pts.length - 1); }
      function y(v) { return P + (hi - v) * (H - 2 * P) / (hi - lo); }
      var line = pts.map(function (v, i) { return x(i).toFixed(1) + ',' + y(v).toFixed(1); }).join(' ');
      var area = 'M' + x(0).toFixed(1) + ',' + (H - P) + ' L' + line.replace(/ /g, ' L') + ' L' + x(pts.length - 1).toFixed(1) + ',' + (H - P) + ' Z';
      var dots = rec.map(function (m, i) {
        return '<circle cx="' + x(i + 1).toFixed(1) + '" cy="' + y(pts[i + 1]).toFixed(1) + '" r="3.5" class="' + (m.won ? 'w' : 'l') + '"><title>' +
          esc(fmtDate(m.ended)) + ' · ' + esc(MAPS[String(m.map || '').toLowerCase()] || m.map) + ' · ' + (m.won ? L.won : L.lost) + ' · ' + Math.round(pts[i + 1]) + '</title></circle>';
      }).join('');
      box.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(L.rating) + ': ' + Math.round(pts[0]) + ' → ' + p.rating + '">' +
        '<path d="' + area + '" class="area"/><polyline points="' + line + '" class="line"/>' + dots + '</svg>' +
        '<div class="pf-scale"><span>' + Math.round(hi) + '</span><span>' + Math.round(lo) + '</span></div>';
    }

    api('/player.json?id=' + id).then(function (p) {
      var r = p.rank || {};
      document.title = p.name + ' · ' + L.profile + ' · TrueCombat: Platinum';
      q('[data-pf-name]').textContent = p.name;
      q('[data-pf-lede]').hidden = true;
      if (search) search.hidden = true;
      var span = r.xpNext ? (r.xp - r.xpThis) / (r.xpNext - r.xpThis) : 1;
      var rank = q('[data-pf-rank]');
      rank.innerHTML = '<div class="pf-rank-top">' + badge(r) + '<b>' + esc(r.title || '') + '</b><span class="muted">' + num(r.xp) + ' XP' +
        (r.xpNext ? ' · ' + num(r.xpNext - r.xp) + ' ' + L.xpTo + ' <span data-next-title></span>' : ' · ' + L.topRank) + '</span></div>' +
        '<div class="xpbar"><i style="width:' + Math.max(0, Math.min(100, span * 100)).toFixed(1) + '%"></i></div>' +
        (p.ranked ? '' : '<p class="muted">' + L.notRanked + '</p>');
      rank.hidden = false;
      if (r.xpNext) api('/ranks.json').then(function (d) {
        var next = (d.ranks || [])[r.level]; var el = rank.querySelector('[data-next-title]'); if (next && el) el.textContent = next.title;
      }, function () {});

      var tiles = [
        [L.rating, num(p.rating), L.peak + ' ' + num(p.peakRating)],
        [L.position, p.position ? '#' + num(p.position) : '–', ''],
        [L.matches, num(p.matches), dur(p.timePlayed)],
        [L.winRate, p.matches ? pct(p.wins / p.matches) : '–', num(p.wins) + ' ' + L.wins.toLowerCase()],
        [L.kills, num(p.kills), num(p.deaths) + ' ' + L.deaths.toLowerCase()],
        [L.kd, kdOf(p).toFixed(2), ''],
        [L.headshots, pct(p.kills ? p.headshots / p.kills : 0), num(p.headshots)],
        [L.damage, num(p.damage), ''],
        [L.roundsWon, num(p.roundsWon), ''],
        [L.objectives, num(p.objectives), ''],
        [L.teamKills, num(p.teamKills), '']
      ];
      q('[data-pf-stats]').innerHTML = tiles.map(function (t) {
        return '<div><span>' + t[0] + '</span><b>' + t[1] + '</b>' + (t[2] ? '<small>' + t[2] + '</small>' : '') + '</div>';
      }).join('');

      var best = Math.max.apply(null, (p.weapons || []).map(function (w) { return w.kills || 0; }).concat([1]));
      q('[data-pf-weapons]').innerHTML = (p.weapons || []).map(function (w) {
        return '<tr><td><b>' + esc(w.name) + '</b><span class="pf-bar"><i style="width:' + ((w.kills || 0) / best * 100).toFixed(1) + '%"></i></span></td><td>' +
          num(w.kills) + '</td><td>' + num(w.headshots) + '</td><td>' + num(w.shots) + '</td><td>' + (w.accuracy == null ? '–' : pct(w.accuracy)) + '</td></tr>';
      }).join('') || '<tr><td colspan="5">–</td></tr>';

      q('[data-pf-matches]').innerHTML = (p.recent || []).map(function (m) {
        var c = m.ratingChange || 0;
        return '<tr><td>' + fmtDate(m.ended) + '</td><td>' + mapLabel(m.map) + '</td><td>' + esc(m.mode || '') + '</td><td class="' + (m.won ? 'up' : 'down') + '">' +
          (m.won ? L.won : L.lost) + '</td><td>' + num(m.kills) + ' / ' + num(m.deaths) + '</td><td>' + num(m.headshots) + '</td><td>+' + num(m.xp) +
          '</td><td class="' + (c > 0 ? 'up' : c < 0 ? 'down' : '') + '">' + (c > 0 ? '+' : '') + c + '</td></tr>';
      }).join('') || '<tr><td colspan="8">–</td></tr>';

      chart(p);

      var foot = q('[data-pf-foot]');
      foot.innerHTML = (p.firstSeen ? L.firstSeen + ' ' + fmtDate(p.firstSeen) : '') + (p.lastSeen ? ' · ' + L.lastSeen + ' ' + fmtDate(p.lastSeen) : '') +
        ' · <button type="button" class="pf-copy">' + L.copyLink + '</button>';
      foot.querySelector('.pf-copy').addEventListener('click', function (e) {
        var b = e.currentTarget;
        (navigator.clipboard ? navigator.clipboard.writeText(location.href) : Promise.reject()).then(function () {
          b.textContent = L.linkCopied; setTimeout(function () { b.textContent = L.copyLink; }, 1600);
        }, function () {});
      });
      q('[data-pf-body]').hidden = false;
    }, function () { missing(L.unknownPlayer); });
  });

  /* ---------- media page: filter tabs and lightbox ---------- */
  $all('[data-gallery]').forEach(function (grid) {
    var shots = $all('.shot', grid);
    var count = document.querySelector('[data-media-count]');
    var filter = document.querySelector('[data-media-filter]');
    function visible() { return shots.filter(function (s) { return !s.hidden; }); }
    if (filter) $all('button[data-cat]', filter).forEach(function (b) {
      b.addEventListener('click', function () {
        $all('button[data-cat]', filter).forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
        var c = b.dataset.cat;
        shots.forEach(function (s) { s.hidden = !(c === 'all' || s.dataset.cat === c); });
        if (count) count.textContent = visible().length + ' ' + L.screenshots;
      });
    });
    var lb = document.querySelector('[data-lightbox]');
    if (!lb) return;
    var img = lb.querySelector('img'), cap = lb.querySelector('figcaption');
    var list = [], at = 0, opener = null;
    function open(i) {
      at = (i + list.length) % list.length;
      var s = list[at], im = s.querySelector('img');
      img.src = im.dataset.full || im.src; img.alt = im.alt;
      cap.textContent = s.querySelector('b').textContent + ' · ' + s.querySelector('figcaption span').textContent;
      lb.hidden = false;
      lb.querySelector('.lb-close').focus();
    }
    function close() { lb.hidden = true; img.removeAttribute('src'); if (opener) opener.focus(); }
    shots.forEach(function (s) {
      s.querySelector('button').addEventListener('click', function (e) { opener = e.currentTarget; list = visible(); open(list.indexOf(s)); });
    });
    lb.querySelector('.lb-close').addEventListener('click', close);
    lb.querySelector('.lb-prev').addEventListener('click', function () { open(at - 1); });
    lb.querySelector('.lb-next').addEventListener('click', function () { open(at + 1); });
    lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
    document.addEventListener('keydown', function (e) {
      if (lb.hidden) return;
      if (e.key === 'Escape') close();
      if (e.key === 'ArrowLeft') open(at - 1);
      if (e.key === 'ArrowRight') open(at + 1);
    });
  });

  /* ---------- click-to-play YouTube (youtube-nocookie, loads only after a click) ---------- */
  $all('[data-yt]').forEach(function (box) {
    var btn = box.querySelector('button');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var f = document.createElement('iframe');
      f.src = 'https://www.youtube-nocookie.com/embed/' + encodeURIComponent(box.dataset.yt) + '?autoplay=1&rel=0&start=' + (parseInt(box.dataset.start, 10) || 0);
      f.title = box.dataset.title || 'YouTube video';
      f.allow = 'autoplay; encrypted-media; picture-in-picture; fullscreen';
      f.allowFullscreen = true;
      box.innerHTML = ''; box.appendChild(f); box.classList.add('playing');
    });
  });

  /* ---------- filter chips (weapons page) ---------- */
  $all('[data-filter-group]').forEach(function (group) {
    var target = document.querySelector(group.dataset.filterGroup);
    $all('button[data-filter]', group).forEach(function (b) {
      b.addEventListener('click', function () {
        $all('button[data-filter]', group).forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
        var f = b.dataset.filter;
        $all('[data-team]', target).forEach(function (card) {
          card.hidden = !(f === 'all' || card.dataset.team === f || card.dataset.team === 'both');
        });
      });
    });
  });

  /* ---------- scroll reveal (progressive: without IntersectionObserver everything is simply shown) ---------- */
  (function () {
    if (!('IntersectionObserver' in window)) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var els = $all('.band .section-head, .feature, .map-card, .trio figure, .clan, .member, .tip, .release, .weapon');
    if (!els.length) return;
    var vh = window.innerHeight || 800;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, sib = el.parentNode ? Array.prototype.indexOf.call(el.parentNode.children, el) : 0;
        el.style.transitionDelay = Math.min(sib, 5) * 60 + 'ms';
        el.classList.add('in'); io.unobserve(el);
      });
    }, { rootMargin: '0px 0px -8% 0px' });
    els.forEach(function (el) {
      if (el.getBoundingClientRect().top < vh) return; /* already on screen: never hide it */
      el.classList.add('rv'); io.observe(el);
    });
    document.documentElement.classList.add('js-reveal');
  })();
})();
