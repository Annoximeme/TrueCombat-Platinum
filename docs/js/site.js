/* TrueCombat: Platinum website: shared script for every page (English and Dutch).
   Sections opt in with data attributes:
     [data-download]              download buttons, pointed at the newest installer (TrueCombat-Platinum-Setup.exe)
     [data-releases="5"|"all"]    patch notes from GitHub Releases (static HTML stays as fallback)
     [data-servers="5"|"all"]     live server list from the bridge (tools/server-bridge)
     [data-leaderboard]           leaderboards from the bridge (rows link to player.html?id=)
     [data-player]                player profile page (player.html?id=<player id>)
     [data-gallery]               screenshot grid with filter tabs and a lightbox (media page)
     [data-yt]                    click-to-play YouTube embed (privacy-enhanced, nothing loads before a click)
     [data-compare] [data-post-filter] [data-copy-link]   devlog sliders, topic filter and copy-link button
     [data-post] [data-rate] [data-post-stat]             devlog reads and star ratings (tools/server-bridge/tcp_devlog.py, no cookies)
     [data-search-open]           opens the site search (also Ctrl+K and /), index in js/search-<lang>.json
   Set TCP_API to the bridge's public https URL once it is hosted. Empty means "offline". */
var TCP_API = 'https://api.truecombat.eu';

(function () {
  var lang = (document.documentElement.lang || 'en').slice(0, 2);
  var DICT = {
    en: {
      months: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
      latest: 'Latest', kindSetupLong: 'Windows installer', kindSetup: 'Installer', kindZip: 'Full game, zip', offline: 'Master server offline', online: 'Online', loading: 'Checking…',
      noServersOffline: 'The live server list is unreachable right now. The Servers tab in the launcher shows the same list.',
      moreNotes: 'Show the full notes', topAll: 'All time', top30: 'Last 30 days', cmpAdd: 'Compare', cmpOn: 'Comparing', cmpTitle: 'Compare weapons', cmpHint: 'Pick up to three weapons to compare.', cmpClear: 'Clear', cmpDmg: 'Damage per hit', cmpRpm: 'Fire rate', cmpDps: 'Damage per second', cmpMag: 'Magazine', cmpEmpty: 'Time to empty', cmpReload: 'Full reload', cmpPellets: 'pellets', cmpNote: 'Body hits before range and armour. Shotguns count every pellet.', lessNotes: 'Show less', liveNow: '{p} playing on {s} servers right now', liveIdle: '{s} servers online right now',
      noServers: 'Nobody is hosting a public server right now. Host one from the launcher with List publicly switched on.',
      players: 'players', servers: 'servers', password: 'Password', ranked: 'Ranked', unranked: 'Unranked', rankedTip: 'Matches count toward the leaderboards', need1: 'Needs 1 player', needN: 'Needs {n} players', needTip: 'A player left mid-match. Fill in now and you cannot lose rating this match.', unrankedTip: 'Matches do not count toward the leaderboards', bot: 'bot', bots: 'bots', copy: 'Copy address', copied: 'Copied',
      updated: 'Updated', join: 'In the launcher: Servers → Join by address',
      lbEmpty: 'No ranked matches yet. Leaderboards fill in once public servers report their matches.',
      lbOffline: 'The leaderboards are temporarily unavailable. Please check back in a few minutes.',
      soon: 'Coming soon', matches: 'matches', rating: 'Rating', peak: 'Peak', kd: 'K/D', headshots: 'Headshots', wins: 'Wins', played: 'Played', accuracy: 'Accuracy',
      xpTo: 'XP to', topRank: 'Highest rank reached', weapons: 'Weapons', recent: 'Recent matches', close: 'Close', notRanked: 'Not ranked yet: finish a match to get ranked.',
      position: 'Position', noPlayer: 'No player found with that name.', unknownPlayer: 'This player has no recorded matches yet.', won: 'Win', lost: 'Loss', hours: 'h', minutes: 'min',
      play: 'Play the trailer', notesFailed: 'GitHub could not be reached. Showing the notes built into this page.',
      kills: 'Kills', deaths: 'Deaths', winRate: 'Win rate', damage: 'Damage', objectives: 'Objectives', roundsWon: 'Rounds won', teamKills: 'Team kills',
      profile: 'Player profile', firstSeen: 'First seen', lastSeen: 'Last seen', copyLink: 'Copy profile link', linkCopied: 'Link copied',
      trendShort: 'Rating history appears after two rated matches.', lastN: 'Last {n} matches', found: '{n} found',
      apiOffline: 'Player stats are offline right now. Please try again in a few minutes.', screenshots: 'screenshots',
      specops: 'SpecOps', terrorists: 'Terrorists', draw: 'Draw', wins_: '{t} win', mvp: 'MVP', score: 'Score', ping: 'Ping', player: 'Player',
      emptyBoard: 'Only bots on the server right now. Join in and take their place.', justNow: 'just now', minAgo: '{n} min ago', hAgo: '{n} h ago', dAgo: '{n} d ago',
      rounds: 'rounds', noResults: 'No completed matches yet. Results appear here the moment a ranked match ends.', resultsOffline: 'Match results are unavailable right now.',
      reads: '{n} reads', read1: '1 read', ratingOf: '{avg} from {n} ratings', topRated: 'Top rated'
    },
    nl: {
      months: ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'],
      latest: 'Nieuwste', kindSetupLong: 'Windows-installatieprogramma', kindSetup: 'Installatieprogramma', kindZip: 'Volledig spel, zip', offline: 'Masterserver offline', online: 'Online', loading: 'Bezig…',
      noServersOffline: 'De live serverlijst is nu niet bereikbaar. Het tabblad Servers in de launcher toont dezelfde lijst.',
      moreNotes: 'Toon alle notities', topAll: 'Altijd', top30: 'Laatste 30 dagen', cmpAdd: 'Vergelijk', cmpOn: 'Vergeleken', cmpTitle: 'Wapens vergelijken', cmpHint: 'Kies tot drie wapens om te vergelijken.', cmpClear: 'Wissen', cmpDmg: 'Schade per treffer', cmpRpm: 'Vuursnelheid', cmpDps: 'Schade per seconde', cmpMag: 'Magazijn', cmpEmpty: 'Tijd tot leeg', cmpReload: 'Volledig herladen', cmpPellets: 'hagels', cmpNote: 'Rompschoten, voor afstand en bepantsering. Bij hagelgeweren telt elke hagel mee.', lessNotes: 'Minder tonen', liveNow: '{p} spelers op {s} servers op dit moment', liveIdle: '{s} servers nu online',
      noServers: 'Er host nu niemand een publieke server. Host er zelf een vanuit de launcher met Openbaar tonen aan.',
      players: 'spelers', servers: 'servers', password: 'Wachtwoord', ranked: 'Ranked', unranked: 'Unranked', rankedTip: 'Potjes tellen mee voor de ranglijsten', need1: 'Zoekt 1 speler', needN: 'Zoekt {n} spelers', needTip: 'Er is iemand vertrokken tijdens het potje. Val nu in en je kunt deze match geen rating verliezen.', unrankedTip: 'Potjes tellen niet mee voor de ranglijsten', bot: 'bot', bots: 'bots', copy: 'Adres kopiëren', copied: 'Gekopieerd',
      updated: 'Bijgewerkt', join: 'In de launcher: Servers → Verbinden met adres',
      lbEmpty: 'Nog geen gerankte potjes. De ranglijsten vullen zich zodra publieke servers hun potjes doorgeven.',
      lbOffline: 'De ranglijsten zijn tijdelijk niet beschikbaar. Probeer het over een paar minuten opnieuw.',
      soon: 'Binnenkort', matches: 'potjes', rating: 'Rating', peak: 'Hoogste', kd: 'K/D', headshots: 'Headshots', wins: 'Winst', played: 'Gespeeld', accuracy: 'Trefzekerheid',
      xpTo: 'XP tot', topRank: 'Hoogste rang bereikt', weapons: 'Wapens', recent: 'Laatste potjes', close: 'Sluiten', notRanked: 'Nog niet gerankt: speel een potje uit.',
      position: 'Positie', noPlayer: 'Geen speler met die naam gevonden.', unknownPlayer: 'Van deze speler zijn nog geen potjes bekend.', won: 'Winst', lost: 'Verlies', hours: 'u', minutes: 'min',
      play: 'Speel de trailer af', notesFailed: 'GitHub was niet bereikbaar. Je ziet de notities die in deze pagina zitten.',
      kills: 'Kills', deaths: 'Doden', winRate: 'Winstpercentage', damage: 'Schade', objectives: 'Doelen', roundsWon: 'Rondes gewonnen', teamKills: 'Teamkills',
      profile: 'Spelersprofiel', firstSeen: 'Eerst gezien', lastSeen: 'Laatst gezien', copyLink: 'Profiellink kopiëren', linkCopied: 'Link gekopieerd',
      trendShort: 'Het ratingverloop verschijnt na twee gerankte potjes.', lastN: 'Laatste {n} potjes', found: '{n} gevonden',
      apiOffline: 'De spelersstatistieken zijn nu offline. Probeer het over een paar minuten opnieuw.', screenshots: 'screenshots',
      specops: 'SpecOps', terrorists: 'Terroristen', draw: 'Gelijkspel', wins_: '{t} winnen', mvp: 'MVP', score: 'Score', ping: 'Ping', player: 'Speler',
      emptyBoard: 'Alleen bots op de server. Doe mee en neem hun plek in.', justNow: 'zojuist', minAgo: '{n} min geleden', hAgo: '{n} u geleden', dAgo: '{n} d geleden',
      rounds: 'rondes', noResults: 'Nog geen voltooide potjes. Uitslagen verschijnen hier zodra een gerankt potje eindigt.', resultsOffline: 'Uitslagen zijn nu niet beschikbaar.',
      reads: '{n} keer gelezen', read1: '1 keer gelezen', ratingOf: '{avg} uit {n} beoordelingen', topRated: 'Best beoordeeld'
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
  /* the home page shows the latest notes folded to a preview, with a toggle for the rest */
  function clampNotes(box) {
    if (box.dataset.releases === 'all') return;
    var rel = box.querySelector('.release[open]'), body = rel && rel.querySelector('.body');
    if (!body || body.dataset.clamped || body.scrollHeight < 760) return;
    body.dataset.clamped = '1'; body.classList.add('clamp');
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'btn btn-ghost notes-more'; b.setAttribute('aria-expanded', 'false'); b.textContent = L.moreNotes;
    b.addEventListener('click', function () {
      var open = body.classList.toggle('clamp') === false;
      b.setAttribute('aria-expanded', String(open)); b.textContent = open ? L.lessNotes : L.moreNotes;
      if (!open) rel.scrollIntoView({ block: 'start' });
    });
    rel.appendChild(b);
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
    clampNotes(box);
    if (location.hash) { var t = document.getElementById(location.hash.slice(1)); if (t && t.tagName === 'DETAILS') { t.open = true; t.scrollIntoView(); } }
  }
  function applyDownload(rels) {
    $all('[data-version]').forEach(function (el) { el.textContent = verOf(rels[0]); });
    /* The installer is small and the launcher fetches the game itself. Older
       releases without one fall back to their full zip so the button always works. */
    var pick = function (re) {
      for (var i = 0; i < rels.length; i++) {
        var a = (rels[i].assets || []).filter(function (x) { return re.test(x.name); })[0];
        if (a) return { rel: rels[i], asset: a };
      }
      return null;
    };
    var found = pick(/^TrueCombat-Platinum-Setup\.exe$/i) || pick(/Windows-x64\.zip$/i);
    if (found) {
      var zip = found.asset, i = rels.indexOf(found.rel);
      var mb = Math.max(1, Math.round(zip.size / 1048576)).toLocaleString(lang) + ' MB';
      $all('[data-size]').forEach(function (el) { el.textContent = mb; });
      $all('[data-date]').forEach(function (el) { el.textContent = fmtDate(rels[i].published_at); });
      $all('[data-download]').forEach(function (el) { el.href = zip.browser_download_url; });
      var setup = /\.exe$/i.test(zip.name);
      $all('[data-kind]').forEach(function (el) {
        el.textContent = setup ? (el.dataset.kind === 'long' ? L.kindSetupLong : L.kindSetup) : L.kindZip;
      });
      return;
    }
  }
  var noteBoxes = $all('[data-releases]');
  noteBoxes.forEach(clampNotes);
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
  /* ---------- support: live donation report (tools/server-bridge/tcp_kofi.py) ---------- */
  (function () {
    var rep = document.querySelector('[data-fund]');
    if (!rep) return;
    var nl = document.documentElement.lang === 'nl';
    var T = nl
      ? { month: 'Maand', in: 'Ontvangen', out: 'Uitgegeven', reserve: 'Reserve', open: 'loopt nog', anon: 'Anoniem', monthly: 'maandelijks',
          now: 'Deze maand', of: 'van', sup: 'Supporters deze maand', none: 'Nog geen bijdragen deze maand. Jij kunt de eerste zijn.',
          months: 'januari februari maart april mei juni juli augustus september oktober november december'.split(' ') }
      : { month: 'Month', in: 'Received', out: 'Spent', reserve: 'Reserve', open: 'in progress', anon: 'Anonymous', monthly: 'monthly',
          now: 'This month', of: 'of', sup: 'Supporters this month', none: 'No contributions yet this month. You could be the first.',
          months: 'January February March April May June July August September October November December'.split(' ') };
    var spent = {};
    try { spent = JSON.parse(rep.getAttribute('data-fund') || '{}'); } catch (e) { spent = {}; }
    function eur(n) { var a = Math.abs(n); return (n < 0 ? '−' : '') + '€' + (Math.round(a * 100) / 100).toLocaleString(nl ? 'nl-BE' : 'en-GB', { minimumFractionDigits: a % 1 ? 2 : 0, maximumFractionDigits: 2 }); }
    function label(key) { var p = key.split('-'); var m = T.months[+p[1] - 1]; return (nl ? m : m) + ' ' + p[0]; }
    api('/funding.json').then(function (d) {
      if (!d || d.schema !== 'tcp-funding/1') return;
      var goal = d.goal || +rep.getAttribute('data-goal') || 150;
      var byMonth = {};
      (d.months || []).forEach(function (m) { byMonth[m.month] = m; });
      var now = new Date(), cur = now.getUTCFullYear() + '-' + ('0' + (now.getUTCMonth() + 1)).slice(-2);
      var keys = Object.keys(byMonth).concat(Object.keys(spent)).filter(function (k, i, a) { return a.indexOf(k) === i; }).sort();
      if (keys.indexOf(cur) < 0) keys.push(cur);
      var reserve = 0, rows = [];
      keys.forEach(function (k) {
        var got = byMonth[k] ? (byMonth[k].received.EUR || 0) : 0;
        var out = spent[k];
        if (out != null) reserve += got - out;
        rows.push('<tr><td>' + esc(label(k)) + '</td><td>' + eur(got) + '</td><td>' + (out != null ? eur(out) : '<span class="dim">' + T.open + '</span>') + '</td><td>' + (out != null ? eur(reserve) : '') + '</td></tr>');
      });
      var m = byMonth[cur], got = m ? (m.received.EUR || 0) : 0, pct = Math.min(100, Math.round(got / goal * 100));
      var sup = m && m.supporters.length
        ? '<ul class="fund-sup">' + m.supporters.map(function (s) { return '<li><b>' + esc(s.name || T.anon) + '</b><span>' + eur(s.amount) + (s.monthly ? ' · ' + T.monthly : '') + '</span></li>'; }).join('') + '</ul>'
        : '<p class="fund-empty">' + T.none + '</p>';
      rep.innerHTML =
        '<div class="fund-now"><div class="fund-now-h"><span>' + T.now + '</span><b>' + eur(got) + '</b> <small>' + T.of + ' ' + eur(goal) + '</small></div>' +
        '<div class="fund-bar" role="progressbar" aria-valuemin="0" aria-valuemax="' + goal + '" aria-valuenow="' + got + '"><i style="width:' + pct + '%"></i></div></div>' +
        '<div class="table-scroll"><table class="fund-table"><thead><tr><th>' + T.month + '</th><th>' + T.in + '</th><th>' + T.out + '</th><th>' + T.reserve + '</th></tr></thead><tbody>' + rows.reverse().join('') + '</tbody></table></div>' +
        '<h4 class="fund-sup-h">' + T.sup + '</h4>' + sup;
    }).catch(function () { /* keep the static report */ });
  })();
  function renderServers(root, data) {
    var limit = root.dataset.servers === 'all' ? 999 : parseInt(root.dataset.servers, 10) || 5;
    var list = (data.servers || []).slice().sort(function (a, b) { return ((b.need || 0) > 0) - ((a.need || 0) > 0) || (b.players || 0) - (a.players || 0); });
    var tbody = root.querySelector('tbody');
    var empty = root.querySelector('.srv-empty');
    var total = list.reduce(function (s, x) { return s + (x.players || 0); }, 0);
    setPill(root, true, list.length + ' ' + L.servers + ' · ' + total + ' ' + L.players);
    if (!list.length) { if (empty) empty.textContent = L.noServers; return; }
    if (empty) empty.hidden = true;
    tbody.innerHTML = list.slice(0, limit).map(function (s) {
      return '<tr><td><b>' + esc(String(s.name || '').replace(/^TrueCombat:\s*Platinum\s*\|\s*/i, '')) + '</b>' + (s.password ? ' <span class="lock" title="' + L.password + '">🔒</span>' : '') +
        (s.ranked === true ? ' <span class="srv-tag ranked" title="' + L.rankedTip + '">' + L.ranked + '</span>' :
         s.ranked === false ? ' <span class="srv-tag" title="' + L.unrankedTip + '">' + L.unranked + '</span>' : '') +
        (s.need > 0 ? ' <span class="srv-tag need" title="' + L.needTip + '">' + (s.need === 1 ? L.need1 : L.needN.replace('{n}', s.need)) + '</span>' : '') +
        '<button type="button" class="addr" data-addr="' + esc(s.address) + '" title="' + L.copy + '">' + esc(s.address) + '</button></td>' +
        '<td>' + mapLabel(s.map) + '</td><td>' + (s.players || 0) + ' / ' + (s.maxPlayers || '?') + (s.bots ? ' <span class="srv-bots">+' + s.bots + ' ' + (s.bots === 1 ? L.bot : L.bots) + '</span>' : '') + '</td><td>' + esc(s.mode || '') + '</td></tr>';
    }).join('');
    renderBoards(list);
    var upd = root.querySelector('.srv-updated');
    if (upd && data.updated) { upd.textContent = L.updated + ' ' + new Date(data.updated).toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' }); upd.hidden = false; }
  }
  /* live scoreboards for every server with someone on it (servers page) */
  var IMG = (lang === 'nl' ? '../' : '') + 'img/';
  function mapArt(m) { var n = MAPS[String(m || '').toLowerCase()]; return IMG + (n ? 'map-' + n.toLowerCase() : 'media-map-vote') + '-640.webp'; }
  function shortName(s) { return String(s || '').replace(/^TrueCombat:\s*Platinum\s*\|\s*/i, ''); }
  function renderBoards(list) {
    var box = document.querySelector('[data-boards]');
    if (!box) return;
    var busy = list.filter(function (s) { return (s.players || 0) + (s.bots || 0) > 0; });
    box.hidden = !busy.length;
    box.querySelector('.boards').innerHTML = busy.map(function (s) {
      var art = mapArt(s.map);
      var rows = (s.playerList || []).map(function (p, i) {
        return '<tr><td class="pos">' + (i + 1) + '</td><td class="who">' + esc(p.name) + '</td><td>' + num(p.score) + '</td><td class="ping">' + (p.ping || 0) + '</td></tr>';
      }).join('');
      return '<article class="board"><header style="background-image:linear-gradient(90deg,rgba(13,16,22,.94) 35%,rgba(13,16,22,.55)),url(' + art + ')">' +
        '<div><h3>' + esc(shortName(s.name)) + '</h3><p>' + mapLabel(s.map) + ' · ' + esc(s.mode || '') + '</p></div>' +
        '<span class="board-count"><b>' + (s.players || 0) + '</b>/' + (s.maxPlayers || '?') + (s.bots ? '<small>+' + s.bots + ' ' + (s.bots === 1 ? L.bot : L.bots) + '</small>' : '') + '</span></header>' +
        (rows ? '<table class="board-table"><thead><tr><th>#</th><th>' + L.player + '</th><th>' + L.score + '</th><th>' + L.ping + '</th></tr></thead><tbody>' + rows + '</tbody></table>'
              : '<p class="board-empty">' + L.emptyBoard + '</p>') +
        '<button type="button" class="addr" data-addr="' + esc(s.address) + '" title="' + L.copy + '">' + esc(s.address) + '</button></article>';
    }).join('');
  }
  var boards = document.querySelector('[data-boards]');
  if (boards) boards.addEventListener('click', function (e) {
    var b = e.target.closest('.addr'); if (!b) return;
    var a = b.dataset.addr;
    (navigator.clipboard ? navigator.clipboard.writeText(a) : Promise.reject()).then(function () {
      b.textContent = L.copied; setTimeout(function () { b.textContent = a; }, 1400);
    }, function () {});
  });

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
    if (TCP_API) setInterval(function () { if (!document.hidden) load(); }, boards ? 30000 : 60000);
  });

  /* latest match results (servers page) */
  function ago(iso) {
    var s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (!(s >= 0)) return '';
    if (s < 90) return L.justNow;
    if (s < 3600) return L.minAgo.replace('{n}', Math.round(s / 60));
    if (s < 86400) return L.hAgo.replace('{n}', Math.round(s / 3600));
    return s < 7 * 86400 ? L.dAgo.replace('{n}', Math.round(s / 86400)) : fmtDate(iso);
  }
  $all('[data-recent]').forEach(function (root) {
    var list = root.querySelector('ol'), empty = root.querySelector('.srv-empty');
    function load() {
      api('/recent.json').then(function (d) {
        var ms = (d.matches || []).slice(0, parseInt(root.dataset.recent, 10) || 8);
        if (!ms.length) { empty.textContent = L.noResults; empty.hidden = false; return; }
        empty.hidden = true;
        list.innerHTML = ms.map(function (m) {
          var art = mapArt(m.map);
          var w = String(m.winner || '').toLowerCase();
          var res = w === 'specops' || w === 'terrorists' ? '<span class="res ' + w + '">' + L.wins_.replace('{t}', L[w]) + '</span>' :
                    (!w && m.rounds > 1 ? '<span class="res">' + L.draw + '</span>' : '');
          var mins = Math.max(1, Math.round((m.duration || 0) / 60));
          var bits = [esc(m.mode || ''), (m.rounds > 1 ? m.rounds + ' ' + L.rounds : ''), mins + ' ' + L.minutes, (m.players || 0) + ' ' + L.players].filter(Boolean).join(' · ');
          var mvp = m.mvp ? '<span class="mvp"><b>' + L.mvp + '</b> <a href="' + esc(profileHref(m.mvp.id)) + '">' + esc(m.mvp.name) + '</a> · ' + m.mvp.kills + ' ' + L.kills.toLowerCase() + '</span>' : '';
          return '<li><img src="' + art + '" alt="" width="120" height="68" loading="lazy"><div class="r-main"><p class="r-top"><b>' + mapLabel(m.map) + '</b>' + res + '</p><p class="r-sub">' + bits + '</p></div>' +
            '<div class="r-side">' + mvp + '<span class="r-when"><time datetime="' + esc(m.ended) + '">' + ago(m.ended) + '</time>' + (m.server ? ' · ' + esc(shortName(m.server)) : '') + '</span></div></li>';
        }).join('');
      }, function () { empty.textContent = L.resultsOffline; empty.hidden = false; });
    }
    load();
    if (TCP_API) setInterval(function () { if (!document.hidden) load(); }, 60000);
  });

  $all('.official .addr').forEach(function (b) {
    b.addEventListener('click', function () {
      var a = b.dataset.addr;
      (navigator.clipboard ? navigator.clipboard.writeText(a) : Promise.reject()).then(function () {
        b.textContent = L.copied; setTimeout(function () { b.textContent = a; }, 1400);
      }, function () {});
    });
  });
  $all('[data-live]').forEach(function (el) {
    api('/servers.json').then(function (d) {
      var list = d.servers || [], p = list.reduce(function (n, x) { return n + (x.players || 0); }, 0);
      if (!list.length) return;
      el.textContent = (p ? L.liveNow : L.liveIdle).replace('{p}', p).replace('{s}', list.length);
      el.hidden = false;
    }, function () {});
  });

  /* top five on the home page: last 30 days, or all time while the month is still quiet */
  $all('[data-top]').forEach(function (root) {
    function show(d, period) {
      var rows = (d.players || []).slice().sort(function (a, b) { return (b.rating || 0) - (a.rating || 0); }).slice(0, 5);
      if (!rows.length) return false;
      root.querySelector('[data-top-period]').textContent = period === '30d' ? L.top30 : L.topAll;
      root.querySelector('ol').innerHTML = rows.map(function (p, i) {
        return '<li><span class="pos">' + (i + 1) + '</span><a class="who" href="' + esc(profileHref(p.id)) + '">' + esc(p.name) + '</a>' + badge(p.rank) +
          '<span class="stat"><b>' + num(p.rating) + '</b> ' + L.rating + '</span><span class="stat"><b>' + kdOf(p).toFixed(2) + '</b> ' + L.kd + '</span></li>';
      }).join('');
      root.hidden = false; return true;
    }
    api('/leaderboard.json?limit=50&period=30d').then(function (d) {
      if (!show(d, '30d')) return api('/leaderboard.json?limit=50&period=all').then(function (a) { show(a, 'all'); });
    }).catch(function () {});
  });

  /* weapon comparison (weapons page): cards carry their stats in data-w */
  (function () {
    var cards = $all('.wcard[data-w]');
    if (!cards.length) return;
    var picked = [];
    var panel = document.createElement('aside');
    panel.className = 'wcompare'; panel.hidden = true; panel.setAttribute('aria-live', 'polite');
    document.body.appendChild(panel);
    function nameOf(c) { return c.querySelector('h3').textContent; }
    function stats(c) {
      var w = JSON.parse(c.dataset.w);
      var full = w.shell ? w.rl * w.mag : w.rl;
      return { dmg: w.dmg, pel: w.pel, rpm: w.rpm, dps: Math.round(w.dmg * w.rpm / 60), mag: w.mag, res: w.res, empty: w.mag / w.rpm * 60, reload: full / 1000 };
    }
    var ROWS = [
      ['cmpDmg', 'dmg', 1, function (s) { return s.dmg + (s.pel ? ' <small>(' + s.pel + ' ' + L.cmpPellets + ')</small>' : ''); }],
      ['cmpRpm', 'rpm', 1, function (s) { return s.rpm + ' <small>rpm</small>'; }],
      ['cmpDps', 'dps', 1, function (s) { return num(s.dps); }],
      ['cmpMag', 'mag', 1, function (s) { return s.mag + ' <small>/ ' + s.res + '</small>'; }],
      ['cmpEmpty', 'empty', 0, function (s) { return s.empty.toFixed(1) + ' s'; }],
      ['cmpReload', 'reload', -1, function (s) { return s.reload.toFixed(1) + ' s'; }]
    ];
    function draw() {
      cards.forEach(function (c) {
        var on = picked.indexOf(c) >= 0, b = c.querySelector('.wc-add');
        c.classList.toggle('picked', on); b.setAttribute('aria-pressed', String(on)); b.textContent = on ? L.cmpOn : L.cmpAdd;
      });
      if (!picked.length) { panel.hidden = true; document.body.classList.remove('has-compare'); return; }
      var ss = picked.map(stats);
      var head = '<tr><th scope="col"><span class="sr-only">' + L.cmpTitle + '</span></th>' + picked.map(function (c, i) {
        return '<th scope="col">' + esc(nameOf(c)) + '<button type="button" class="wc-x" data-i="' + i + '" aria-label="' + L.close + ': ' + esc(nameOf(c)) + '">×</button></th>';
      }).join('') + '</tr>';
      var body = ROWS.map(function (r) {
        var vals = ss.map(function (s) { return s[r[1]]; });
        var best = r[2] > 0 ? Math.max.apply(null, vals) : r[2] < 0 ? Math.min.apply(null, vals) : null;
        return '<tr><th scope="row">' + L[r[0]] + '</th>' + ss.map(function (s, i) {
          var win = best !== null && ss.length > 1 && vals[i] === best;
          return '<td' + (win ? ' class="best"' : '') + '>' + r[3](s) + '</td>';
        }).join('') + '</tr>';
      }).join('');
      panel.innerHTML = '<div class="wrap"><header><h2>' + L.cmpTitle + '</h2><span class="muted">' + (picked.length < 3 ? L.cmpHint : '') + '</span>' +
        '<button type="button" class="btn btn-ghost wc-clear">' + L.cmpClear + '</button><button type="button" class="wc-min" aria-expanded="' + !panel.classList.contains('min') + '" aria-label="' + L.cmpTitle + '">' + CHEV + '</button></header>' +
        '<div class="table-scroll"><table>' + head + body + '</table></div><p class="wnote">' + L.cmpNote + '</p></div>';
      panel.hidden = false; document.body.classList.add('has-compare');
    }
    panel.addEventListener('click', function (e) {
      if (e.target.closest('.wc-clear')) { picked = []; panel.classList.remove('min'); draw(); return; }
      var m = e.target.closest('.wc-min'); if (m) { m.setAttribute('aria-expanded', String(!panel.classList.toggle('min'))); return; }
      var x = e.target.closest('.wc-x'); if (x) { picked.splice(+x.dataset.i, 1); draw(); }
    });
    cards.forEach(function (c) {
      var b = document.createElement('button');
      b.type = 'button'; b.className = 'wc-add'; b.textContent = L.cmpAdd; b.setAttribute('aria-pressed', 'false');
      c.querySelector('header').appendChild(b);
      b.addEventListener('click', function () {
        var i = picked.indexOf(c);
        if (i >= 0) picked.splice(i, 1); else { if (picked.length >= 3) picked.shift(); picked.push(c); }
        draw();
      });
    });
  })();

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

  /* ---------- map layouts: bomb or flag objectives, location names on or off ---------- */
  $all('[data-layout]').forEach(function (lo) {
    lo.addEventListener('click', function (e) {
      var m = e.target.closest('[data-lo-mode]'), c = e.target.closest('[data-lo-call]');
      if (m) {
        lo.dataset.mode = m.dataset.loMode;
        $all('[data-lo-mode]', lo).forEach(function (b) { b.setAttribute('aria-pressed', String(b === m)); });
      }
      if (c) {
        var on = c.getAttribute('aria-pressed') !== 'true';
        c.setAttribute('aria-pressed', String(on));
        lo.classList.toggle('no-call', !on);
      }
    });
  });

  /* ---------- devlog: before/after sliders, topic filter, copy link ---------- */
  $all('[data-compare]').forEach(function (cmp) {
    var r = cmp.querySelector('input[type=range]');
    if (r) r.addEventListener('input', function () { cmp.style.setProperty('--pos', r.value + '%'); });
  });
  $all('[data-post-filter]').forEach(function (bar) {
    var list = document.querySelector('[data-post-list]');
    if (!list) return;
    bar.hidden = false;
    bar.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-tag]');
      if (!b) return;
      var tag = b.dataset.tag;
      $all('button[data-tag]', bar).forEach(function (x) { x.setAttribute('aria-pressed', String(x === b)); });
      $all('.post-card', list).forEach(function (c) { c.hidden = !!tag && c.dataset.tag !== tag; });
      list.classList.toggle('filtered', !!tag);
    });
  });
  $all('[data-copy-link]').forEach(function (b) {
    b.addEventListener('click', function () {
      var label = b.textContent, link = location.href.split('#')[0];
      (navigator.clipboard ? navigator.clipboard.writeText(link) : Promise.reject()).then(function () {
        b.textContent = b.dataset.done; setTimeout(function () { b.textContent = label; }, 1600);
      }, function () {});
    });
  });

  /* ---------- devlog reads and ratings: anonymous, no cookies (see tcp_devlog.py) ---------- */
  (function () {
    if (!TCP_API) return;
    var base = TCP_API.replace(/\/$/, '') + '/devlog/';
    function send(path, obj) {
      // text/plain keeps this a simple request (no CORS preflight); the service reads it as JSON
      return fetch(base + path, { method: 'POST', body: JSON.stringify(obj), headers: { 'Content-Type': 'text/plain' }, keepalive: true, credentials: 'omit' })
        .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
    }
    function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

    var post = document.querySelector('[data-post]');
    if (post) {
      // a read counts once the post has been on screen for 10 seconds; "read to the end" once the
      // reader reaches the end of the post after spending at least 40% of its read time on it
      var slug = post.dataset.post, shown = 0, last = document.hidden ? 0 : Date.now(), read = false, finished = false, atEnd = false;
      var need = Math.max(20000, (+post.dataset.min || 1) * 60000 * 0.4);
      var end = document.querySelector('.post-end');
      if (end && 'IntersectionObserver' in window) {
        new IntersectionObserver(function (es, io) { if (es.some(function (e) { return e.isIntersecting; })) { atEnd = true; io.disconnect(); } }).observe(end);
      }
      var tick = setInterval(function () {
        var now = Date.now();
        if (!document.hidden && last) shown += now - last;
        last = document.hidden ? 0 : now;
        if (!read && shown >= 10000) { read = true; send('read', { slug: slug }).catch(function () {}); }
        if (read && !finished && atEnd && shown >= need) { finished = true; send('done', { slug: slug }).catch(function () {}); }
        if (finished || (read && !end)) clearInterval(tick);
      }, 1000);
    }

    $all('[data-rate]').forEach(function (box) {
      var slug = box.dataset.rate, group = box.querySelector('.rate-stars'), note = box.querySelector('.rate-note');
      var btns = $all('button', group), key = 'tcp-rate-' + slug;
      function paint(n) { btns.forEach(function (b, i) { b.classList.toggle('on', i < n); b.setAttribute('aria-checked', String(i + 1 === n)); b.tabIndex = (n ? i + 1 === n : i === 0) ? 0 : -1; }); }
      var mine = store(key) || '';
      var m = /^(\d{4}-\d\d-\d\d):([1-5])$/.exec(mine);
      paint(m ? +m[2] : 0);
      function vote(n) {
        group.setAttribute('aria-busy', 'true');
        send('rate', { slug: slug, stars: n }).then(function () {
          paint(n);
          store(key, new Date().toISOString().slice(0, 10) + ':' + n);
          note.textContent = box.dataset.thanks;
        }, function () { note.textContent = box.dataset.fail; }).then(function () { group.removeAttribute('aria-busy'); });
      }
      group.addEventListener('click', function (e) { var b = e.target.closest('button[data-stars]'); if (b) vote(+b.dataset.stars); });
      group.addEventListener('keydown', function (e) {
        var i = btns.indexOf(document.activeElement); if (i < 0) return;
        var j = e.key === 'ArrowRight' || e.key === 'ArrowUp' ? Math.min(4, i + 1) : e.key === 'ArrowLeft' || e.key === 'ArrowDown' ? Math.max(0, i - 1) : -1;
        if (j < 0) return;
        e.preventDefault(); btns[j].focus();
      });
    });

    var slots = $all('[data-post-stat]'), boxes = $all('[data-rate]');
    if (!slots.length && !boxes.length) return;
    fetch(base + 'public.json', { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
      boxes.forEach(function (box) { box.hidden = false; });  // only offer ratings when the service is up
      var posts = d.posts || {}, best = null;
      // the best-rated post (5+ ratings, 4.0 or higher) gets a "Top rated" mark
      Object.keys(posts).forEach(function (k) { var p = posts[k]; if (p.rating >= 4 && (!best || p.rating > posts[best].rating || (p.rating === posts[best].rating && p.ratings > posts[best].ratings))) best = k; });
      var fmt = function (n) { return Number(n).toLocaleString(lang === 'nl' ? 'nl-BE' : 'en-GB'); };
      slots.forEach(function (el) {
        var p = posts[el.dataset.postStat]; if (!p) return;
        var bits = [];
        if (p.rating) bits.push('<b>★ ' + esc(p.rating.toFixed(1)) + '</b>');
        if (p.reads) bits.push(esc(p.reads === 1 ? L.read1 : L.reads.replace('{n}', fmt(p.reads))));
        if (!bits.length) return;
        el.innerHTML = (el.dataset.postStat === best ? '<span class="top">' + esc(L.topRated) + '</span>' : '') + bits.join(' · ');
        if (p.rating) el.title = L.ratingOf.replace('{avg}', p.rating.toFixed(1)).replace('{n}', fmt(p.ratings));
        el.hidden = false;
      });
    }).catch(function () {});
  })();

  /* ---------- scroll reveal (progressive: without IntersectionObserver everything is simply shown) ---------- */
  (function () {
    if (!('IntersectionObserver' in window)) return;
    if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    var els = $all('.band .section-head, .feature, .map-card, .trio figure, .clan, .member, .tip, .release, .weapon, .post-card');
    if (!els.length) return;
    var vh = window.innerHeight || 800;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        /* reveal on entry, and also anything already scrolled past (fast scrolls, anchor jumps) */
        if (!en.isIntersecting && en.boundingClientRect.top > 0) return;
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

  /* ---------- site search (Ctrl+K, / or the magnifier in the top bar) ----------
     The index (js/search-<lang>.json, written by tools/website/build.py) is only fetched the first time search opens. */
  (function () {
    var T = lang === 'nl'
      ? { ph: 'Zoek maps, wapens, gidsen en posts', none: 'Niets gevonden voor', hint: '↑ ↓ kiezen · Enter openen · Esc sluiten', label: 'Zoeken op de site', quick: 'Snel naar', fail: 'Zoeken is nu niet beschikbaar.' }
      : { ph: 'Search maps, weapons, guides and posts', none: 'Nothing found for', hint: '↑ ↓ to move · Enter to open · Esc to close', label: 'Search the site', quick: 'Jump to', fail: 'Search is unavailable right now.' };
    var script = document.querySelector('script[src*="js/site.js"]');
    if (!script || !window.HTMLDialogElement) { $all('[data-search-open]').forEach(function (b) { b.hidden = true; }); return; }
    var jsBase = new URL('.', script.src), root = new URL(lang === 'nl' ? '../nl/' : '../', jsBase);
    var QUICK = ['download.html', 'servers.html', 'guide.html', 'maps.html', 'weapons.html', 'faq.html'];
    var dlg, input, list, rows = null, shown = [], sel = 0;

    function norm(t) { return (t || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, ''); }
    function find(q) {
      var words = norm(q).split(/\s+/).filter(Boolean);
      if (!words.length) return QUICK.map(function (u) { return rows.filter(function (r) { return r.u === u; })[0]; }).filter(Boolean);
      var out = [];
      rows.forEach(function (r, i) {
        var score = 0;
        for (var w = 0; w < words.length; w++) {
          var x = words[w], at = r.nt.indexOf(x), s = 0;
          if (at === 0) s = 100; else if (at > 0 && /[^a-z0-9]/.test(r.nt.charAt(at - 1))) s = 70; else if (at > 0) s = 45;
          else if (r.nk.indexOf(x) === 0) s = 25; else if (r.nd.indexOf(x) >= 0) s = 12;
          if (!s) return;
          score += s;
        }
        if (r.nt === words.join(' ')) score += 60;
        out.push({ r: r, s: score - i / 1000 });
      });
      out.sort(function (a, b) { return b.s - a.s; });
      return out.slice(0, 8).map(function (o) { return o.r; });
    }
    function draw() {
      var q = input.value.trim();
      if (!rows) { list.innerHTML = ''; return; }
      shown = find(q); sel = 0;
      if (!shown.length) { list.innerHTML = '<li class="sr-empty">' + esc(T.none) + ' “' + esc(q) + '”</li>'; return; }
      list.innerHTML = (q ? '' : '<li class="sr-head">' + esc(T.quick) + '</li>') + shown.map(function (r, i) {
        return '<li role="option" id="sr-' + i + '" aria-selected="' + (i === 0) + '"><a href="' + esc(new URL(r.u, root).href) + '" tabindex="-1"><span class="sr-k">' + esc(r.k) + '</span><span class="sr-t">' + esc(r.t) + '</span>' + (r.d ? '<span class="sr-d">' + esc(r.d) + '</span>' : '') + '</a></li>';
      }).join('');
      input.setAttribute('aria-activedescendant', 'sr-0');
    }
    function move(d) {
      if (!shown.length) return;
      sel = (sel + d + shown.length) % shown.length;
      $all('[role=option]', list).forEach(function (li, i) { li.setAttribute('aria-selected', i === sel); if (i === sel) li.scrollIntoView({ block: 'nearest' }); });
      input.setAttribute('aria-activedescendant', 'sr-' + sel);
    }
    function build() {
      dlg = document.createElement('dialog');
      dlg.className = 'search';
      dlg.setAttribute('aria-label', T.label);
      dlg.innerHTML = '<form method="dialog" class="sr-box"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>' +
        '<input type="search" autocomplete="off" spellcheck="false" enterkeyhint="go" role="combobox" aria-expanded="true" aria-controls="sr-list" aria-label="' + esc(T.label) + '" placeholder="' + esc(T.ph) + '"><kbd>Esc</kbd></form>' +
        '<ul id="sr-list" role="listbox" aria-label="' + esc(T.label) + '"></ul><p class="sr-hint">' + esc(T.hint) + '</p>';
      document.body.appendChild(dlg);
      input = dlg.querySelector('input'); list = dlg.querySelector('ul');
      input.addEventListener('input', draw);
      input.addEventListener('keydown', function (e) {
        if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
        else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
        else if (e.key === 'Escape') { e.preventDefault(); dlg.close(); }  /* a search field would only clear itself first */
        else if (e.key === 'Enter') { e.preventDefault(); var a = list.querySelector('[aria-selected=true] a'); if (a) { dlg.close(); location.href = a.href; } }
      });
      dlg.addEventListener('click', function (e) { if (e.target === dlg || e.target.closest('a')) dlg.close(); });
      dlg.querySelector('kbd').addEventListener('click', function () { dlg.close(); });
    }
    function open() {
      if (!dlg) build();
      if (dlg.open) return;
      var menu = document.getElementById('menu'); if (menu) menu.open = false;
      input.value = ''; dlg.showModal(); input.focus();
      if (rows) { draw(); return; }
      fetch(new URL('search-' + (lang === 'nl' ? 'nl' : 'en') + '.json', jsBase), { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
        rows = d.map(function (r) { r.nt = norm(r.t); r.nd = norm(r.d); r.nk = norm(r.k); return r; });
        draw();
      }).catch(function () { list.innerHTML = '<li class="sr-empty">' + esc(T.fail) + '</li>'; });
    }
    $all('[data-search-open]').forEach(function (b) { b.addEventListener('click', open); });
    document.addEventListener('keydown', function (e) {
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test((e.target.tagName || '')) || e.target.isContentEditable;
      if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey) && !e.altKey) { e.preventDefault(); open(); }
      else if (e.key === '/' && !typing && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); open(); }
    });
  })();

  /* ---------- back to top, and the section rail on the home page ---------- */
  (function () {
    var label = lang === 'nl' ? 'Terug naar boven' : 'Back to top';
    var top = document.createElement('button');
    top.type = 'button'; top.className = 'to-top'; top.setAttribute('aria-label', label); top.title = label; top.hidden = true;
    top.innerHTML = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 14l6-6 6 6"/></svg>';
    top.addEventListener('click', function () {
      var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      window.scrollTo({ top: 0, behavior: calm ? 'auto' : 'smooth' });
    });
    document.body.appendChild(top);
    var ticking = false;
    function check() { ticking = false; top.hidden = window.scrollY < 1400; }
    window.addEventListener('scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(check); } }, { passive: true });
    check();

    /* the home page is long: a rail of section markers shows where you are and jumps between sections */
    var hero = document.querySelector('.hero');
    if (!hero || !('IntersectionObserver' in window)) return;
    var secs = $all('main > section[id]').filter(function (s) { return s.querySelector('.eyebrow') && s.querySelector('h2'); });
    if (secs.length < 4) return;
    var rail = document.createElement('nav');
    rail.className = 'rail'; rail.setAttribute('aria-label', lang === 'nl' ? 'Op deze pagina' : 'On this page');
    rail.innerHTML = secs.map(function (s) { return '<a href="#' + esc(s.id) + '"><span>' + esc(s.querySelector('.eyebrow').textContent.trim()) + '</span></a>'; }).join('');
    document.body.appendChild(rail);
    var links = $all('a', rail);
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var i = secs.indexOf(en.target);
        links.forEach(function (a, j) { if (j === i) a.setAttribute('aria-current', 'true'); else a.removeAttribute('aria-current'); });
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    secs.forEach(function (s) { io.observe(s); });
    new IntersectionObserver(function (e) { rail.classList.toggle('on', !e[0].isIntersecting); }).observe(hero);
  })();

  /* ---------- cards catch the light under the cursor (mouse only) ---------- */
  (function () {
    if (!window.matchMedia || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
    var cards = $all('.feature, .wcard, .reqs, .post-card, .member, .steps-flow li, .faq > div');
    cards.forEach(function (el) {
      if (getComputedStyle(el, '::after').content !== 'none') return;  /* keep cards that already use ::after */
      el.classList.add('lit');
      el.addEventListener('pointermove', function (e) {
        var r = el.getBoundingClientRect();
        el.style.setProperty('--mx', (e.clientX - r.left) + 'px');
        el.style.setProperty('--my', (e.clientY - r.top) + 'px');
      });
    });
  })();

  /* ---------- cinematic layer: hero depth and compass, count-up numbers, ghost lettering, map theatre, tilt ---------- */
  (function () {
    var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var mouse = window.matchMedia && window.matchMedia('(hover: hover) and (pointer: fine)').matches;
    var hasIO = 'IntersectionObserver' in window;

    /* hero: the backdrop, fog and copy shift a few pixels against the cursor, and the compass tape turns with it */
    var hero = document.querySelector('.hero'), tape = document.getElementById('tape');
    if (hero) {
      if (tape) {
        var marks = ['N', '15', '30', 'NE', '60', '75', 'E', '105', '120', 'SE', '150', '165', 'S', '195', '210', 'SW', '240', '255', 'W', '285', '300', 'NW', '330', '345'], html = '';
        for (var r = 0; r < 3; r++) marks.forEach(function (m) { html += '<span' + (/^[NESW]+$/.test(m) ? ' class="c"' : '') + '>' + m + '</span>'; });
        tape.innerHTML = html;
      }
      var tx = 0, ty = 0, cx = 0, cy = 0, heading = 0, seen = true, raf = 0, last = 0, LOOP = 24 * 60;
      function frame(now) {
        raf = 0;
        var dt = Math.min(50, now - (last || now)); last = now;
        cx += (tx - cx) * 0.06; cy += (ty - cy) * 0.06;
        heading = (heading + dt * 0.006 + cx * dt * 0.05 + LOOP) % LOOP;   /* a slow turn, faster when the cursor leans */
        hero.style.setProperty('--px', cx.toFixed(4)); hero.style.setProperty('--py', cy.toFixed(4));
        if (tape) tape.style.transform = 'translate3d(' + (-(LOOP + heading)).toFixed(1) + 'px,0,0)';
        if (seen && !document.hidden) raf = requestAnimationFrame(frame);
      }
      function kick() { if (!raf && seen && !calm) { last = 0; raf = requestAnimationFrame(frame); } }
      if (tape) tape.style.transform = 'translate3d(' + (-LOOP) + 'px,0,0)';
      if (!calm) {
        if (mouse) hero.addEventListener('pointermove', function (e) {
          var b = hero.getBoundingClientRect();
          tx = ((e.clientX - b.left) / b.width - 0.5) * 2; ty = ((e.clientY - b.top) / b.height - 0.5) * 2;
        });
        hero.addEventListener('pointerleave', function () { tx = 0; ty = 0; });
        if (hasIO) new IntersectionObserver(function (e) { seen = e[0].isIntersecting; hero.classList.toggle('offscreen', !seen); kick(); }).observe(hero);
        document.addEventListener('visibilitychange', kick);
        kick();
      }
    }

    /* numbers count up the first time they scroll into view */
    var counts = $all('[data-count], .stats-row dd').filter(function (el) { return /^\d+$/.test(el.textContent.trim()); });
    if (counts.length && hasIO && !calm) {
      var cio = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (!en.isIntersecting) return;
          var el = en.target, end = +el.dataset.to, t0 = 0;
          cio.unobserve(el);
          (function step(now) {
            if (!t0) t0 = now;
            var k = Math.min(1, (now - t0) / 1100), e = 1 - Math.pow(1 - k, 3);
            el.textContent = Math.round(end * e);
            if (k < 1) requestAnimationFrame(step);
          })(performance.now());
        });
      }, { threshold: 0.6 });
      counts.forEach(function (el) { el.dataset.to = el.textContent.trim(); el.style.minWidth = el.offsetWidth + 'px'; el.style.display = 'inline-block'; cio.observe(el); });
    }

    /* ghost lettering: each section's label, outlined and oversized, behind its heading */
    $all('.band .section-head, .page-head .wrap').forEach(function (head) {
      if (head.closest('.post-head, .studio-hero, #maps')) return;
      var eb = head.querySelector('.eyebrow'); if (!eb) return;
      var word = eb.textContent.trim(); if (!word || /^\d+$/.test(word)) return;
      if (word.length > 13) word = word.split(/\s+/).sort(function (a, b) { return b.length - a.length; })[0];
      var g = document.createElement('span');
      g.className = 'ghost'; g.setAttribute('aria-hidden', 'true'); g.textContent = word;
      head.appendChild(g);
    });

    /* map theatre on the home page */
    var maps = document.getElementById('maps'), cards = maps ? $all('.map-card', maps) : [];
    if (hero && cards.length > 2 && mouse && window.innerWidth >= 1000) {
      var bg = document.createElement('div'), word = document.createElement('div'), bar = document.createElement('div');
      bg.className = 'th-bg'; word.className = 'th-word'; bar.className = 'th-bar'; bar.innerHTML = '<i></i>';
      [bg, word, bar].forEach(function (el) { el.setAttribute('aria-hidden', 'true'); });
      var imgs = cards.map(function (c, i) {
        var small = c.querySelector('img'), im = document.createElement('img');
        im.alt = ''; im.decoding = 'async'; im.dataset.src = small.getAttribute('src').replace('-640.webp', '.webp');
        c.dataset.n = '0' + (i + 1);
        bg.appendChild(im); return im;
      });
      maps.classList.add('theatre');
      maps.insertBefore(bg, maps.firstChild); maps.appendChild(word); maps.appendChild(bar);
      var at = -1, timer = 0, hold = false, live = false, MS = 5200, fill = bar.firstChild;
      maps.style.setProperty('--th-ms', MS + 'ms');
      function load(i) { var im = imgs[i]; if (im && im.dataset.src) { im.src = im.dataset.src; delete im.dataset.src; } }
      function show(i, auto) {
        i = (i + cards.length) % cards.length;
        if (i !== at) {
          at = i; load(i); load((i + 1) % cards.length);
          cards.forEach(function (c, k) { c.classList.toggle('on', k === i); });
          imgs.forEach(function (im, k) { im.classList.toggle('on', k === i); });
          word.textContent = cards[i].querySelector('b').textContent;
          word.classList.remove('swap'); void word.offsetWidth; word.classList.add('swap');
        }
        clearTimeout(timer); fill.classList.remove('run');
        if (live && !hold && !calm) { void fill.offsetWidth; fill.classList.add('run'); timer = setTimeout(function () { show(at + 1, true); }, MS); }
      }
      cards.forEach(function (c, i) {
        c.addEventListener('pointerenter', function () { hold = true; show(i); });
        c.addEventListener('focus', function () { hold = true; show(i); });
        c.addEventListener('blur', function () { hold = false; show(at); });
      });
      maps.addEventListener('pointerleave', function () { hold = false; show(at); });
      if (hasIO) new IntersectionObserver(function (e) { live = e[0].isIntersecting; if (live) show(at < 0 ? 0 : at); else { clearTimeout(timer); fill.classList.remove('run'); } }, { rootMargin: '200px 0px' }).observe(maps);
      else { live = true; show(0); }
    }

    /* shots and promo cards lean towards the cursor */
    if (mouse && !calm) {
      $all('.shot, .trio figure, .promo-card, .vf').forEach(function (el) {
        if (el.closest('.lightbox') || el.querySelector('input, iframe, [data-yt], video')) return;
        var g = document.createElement('i'); g.className = 'glare'; g.setAttribute('aria-hidden', 'true');
        if (getComputedStyle(el).position === 'static') el.style.position = 'relative';
        el.appendChild(g); el.classList.add('tilt');
        el.addEventListener('pointermove', function (e) {
          var b = el.getBoundingClientRect(), x = (e.clientX - b.left) / b.width, y = (e.clientY - b.top) / b.height;
          el.classList.add('live');
          el.style.setProperty('--ry', ((x - 0.5) * 5).toFixed(2) + 'deg'); el.style.setProperty('--rx', ((0.5 - y) * 4).toFixed(2) + 'deg');
          el.style.setProperty('--gx', (x * 100).toFixed(1) + '%'); el.style.setProperty('--gy', (y * 100).toFixed(1) + '%');
        });
        el.addEventListener('pointerleave', function () { el.classList.remove('live'); el.style.setProperty('--rx', '0deg'); el.style.setProperty('--ry', '0deg'); });
      });
    }

    /* framed images wipe open on scroll */
    if (hasIO && !calm && document.documentElement.classList.contains('js-reveal')) {
      var wio = new IntersectionObserver(function (entries) { entries.forEach(function (en) { if (en.isIntersecting || en.boundingClientRect.top < 0) { en.target.classList.add('in'); wio.unobserve(en.target); } }); }, { rootMargin: '0px 0px -12% 0px' });
      $all('.vf img, .shot-wide img').forEach(function (im) { if (im.getBoundingClientRect().top < (window.innerHeight || 800)) return; im.classList.add('wipe'); wio.observe(im); });
    }
  })();
})();
