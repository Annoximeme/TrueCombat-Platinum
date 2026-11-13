/* TrueCombat: Platinum website: shared script for every page (English and Dutch).
   Sections opt in with data attributes:
     [data-download]              download buttons, pointed at the newest installer (TrueCombat-Platinum-Setup.exe)
     [data-releases="5"|"all"]    patch notes from GitHub Releases (static HTML stays as fallback)
     [data-servers="5"|"all"]     live server list from the bridge (tools/server-bridge)
     [data-leaderboard]           leaderboards from the bridge (rows link to player?id=)
     [data-player]                player profile page (player?id=<player id>)
     [data-gallery]               screenshot grid with filter tabs and a lightbox (media page)
     [data-yt]                    click-to-play YouTube embed (privacy-enhanced, nothing loads before a click)
     [data-compare] [data-post-filter] [data-copy-link]   devlog sliders, topic filter and copy-link button
     [data-post] [data-rate] [data-post-stat]             devlog reads and star ratings (tools/server-bridge/tcp_devlog.py, no cookies)
     [data-search-open]           opens the site search (also Ctrl+K and /), index in js/search-<lang>.json
   Every page also sends one cookie-free page view, and download clicks, to tools/server-bridge/tcp_insights.py
   (no cookies, nothing stored in the browser; skipped for Global Privacy Control and Do Not Track).
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
      players: 'players', servers: 'servers', password: 'Password', ranked: 'Ranked', unranked: 'Unranked', rankedTip: 'Matches count toward the leaderboards', need1: 'Needs 1 player', needN: 'Needs {n} players', needTip: 'A player left mid-match. Fill in now and you cannot lose rating this match.', unrankedTip: 'Matches do not count toward the leaderboards', bot: 'bot', bots: 'bots', copy: 'Copy address', copied: 'Copied', verified: 'Verified', verifiedTip: 'Checked by the TrueCombat: Platinum team', eac: 'Anti-cheat', eacTip: 'Protected by Easy Anti-Cheat', eacReqTip: 'Protected by Easy Anti-Cheat. Required to join.', joinBtn: 'Join',
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
      matchReport: 'Match report', matchOn: '{mode} on {map}', matchCopy: 'Copy match link', topWeapon: 'Top weapon', map: 'Map', mode: 'Mode', length: 'Length', server: 'Server', unknownMatch: 'This match could not be found.', viewMatch: 'Match report', noTeam: 'Players', version: 'Version',
      reads: '{n} reads', read1: '1 read', ratingOf: '{avg} from {n} ratings', topRated: 'Top rated',
      statLeaders: 'Stat leaders', statNote: 'Verified matches with anti-cheat on, against real players only.', scopeAll: 'All verified', scopeRanked: 'Ranked only',
      allMaps: 'All maps', allModes: 'All modes', allWeapons: 'All weapons', p7: '7 days', p30: '30 days', pAll: 'All time', statPick: 'Stat',
      minSample: 'Shows players with at least {n} {what}.', boardEmpty: 'No verified matches for this selection yet.', value: 'Value',
      secCombat: 'Combat', secPlay: 'Playstyle', secObj: 'Objectives and rounds', secHits: 'Where the hits land', secMaps: 'Maps', secModes: 'Modes',
      secRivals: 'Rivals', secActivity: 'Activity', nemesis: 'Nemesis', nemesisTip: 'Killed this player the most', victim: 'Favourite target',
      victimTip: 'This player killed them the most', h2h: 'Head to head', compareWith: 'Compare with another player', h2hKills: 'Kills on each other',
      h2hAgainst: 'Matches as opponents', h2hTogether: 'Matches as teammates', h2hWins: 'Wins against each other', head: 'Head', body: 'Body', legs: 'Legs',
      accNote: 'Accuracy counts matches without bots only. Hit locations count every hit on a real player.', detailEmpty: 'Detailed stats start with version 0.35.0.',
      detailNote: 'Counted from verified matches with anti-cheat on, against real players only. Bots, warm-up and idle time never count.',
      kills_on: '{n} kills', perDay: '{n} matches', less: 'Less', more: 'More', matchesN: '{n} matches', m: 'm',
      s_kills: 'Kills', s_deaths: 'Deaths', s_assists: 'Assists', s_headshots: 'Headshot kills', s_damage: 'Damage dealt', s_damageTaken: 'Damage taken',
      s_kd: 'K/D', s_headshotRate: 'Headshot rate', s_accuracy: 'Accuracy', s_headHitRate: 'Head hits', s_adr: 'Damage per round', s_winRate: 'Win rate',
      s_kpm: 'Kills per minute', s_avgKillDistance: 'Average kill distance', s_longestKill: 'Longest kill', s_bestStreak: 'Best streak',
      s_doubleKills: 'Double kills', s_tripleKills: 'Triple kills', s_quadKills: 'Quad kills', s_openingKills: 'Opening kills', s_openingDeaths: 'Opening deaths',
      s_clutches: 'Clutches won', s_bestClutch: 'Best clutch', s_trades: 'Trade kills', s_revenges: 'Revenge kills', s_knifeKills: 'Knife kills',
      s_grenadeKills: 'Grenade kills', s_aimedKills: 'Aimed kills', s_hipKills: 'Hip-fire kills', s_standKills: 'Standing kills', s_crouchKills: 'Crouching kills',
      s_proneKills: 'Prone kills', s_leanKills: 'Leaning kills', s_airKills: 'Airborne kills', s_objectives: 'Objectives', s_captures: 'Flag captures',
      s_plants: 'Bomb plants', s_defuses: 'Bomb defuses', s_returns: 'Flag returns', s_roundsWon: 'Rounds won', s_roundMvps: 'Round MVPs', s_wins: 'Match wins',
      s_matches: 'Matches', s_timePlayed: 'Time played', s_xp: 'Experience', s_shots: 'Shots', s_hitsAll: 'Hits',
      verified: 'Verified account', noProfile: 'There is no public profile with that name.',
      acctLedeIn: 'Signed in. Link every PC you play on and your record follows you.', acctFree: 'Available.', acctChecking: 'Checking…',
      acctRenameIn: 'You can change your name again in {n} days.', acctRenameNow: 'You can change your name once every 30 days. Your old name stays held for you for 30 days.', acctNameFree: 'Your name was released after a year away and someone else has taken it. Pick a new one below.',
      acctPcs: '{n} of 8', acctLinkedOn: 'linked {d}', acctUnlink: 'Unlink', acctSure: 'Unlink this PC?', acctNoPcs: 'No PC linked yet. Open this page on the PC you play on and press Link this PC.',
      acctLinkOpen: 'Waiting for the launcher. Approve the link there. Nothing happened? Update the launcher, then try again.',
      acctLinkDone: 'This PC is linked. Your record now follows you.', acctLinkExpired: 'The link code expired. Press Link this PC to try again.',
      acctSigninFailed: 'Sign-in did not finish. Please try again.', acctSigninDiscord: 'Discord did not answer. Please try again in a minute.',
      acctSigninSlow: 'Too many sign-ins from here. Please wait a few minutes.', acctOnDiscord: 'on Discord'
    },
    nl: {
      months: ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'],
      latest: 'Nieuwste', kindSetupLong: 'Windows-installatieprogramma', kindSetup: 'Installatieprogramma', kindZip: 'Volledig spel, zip', offline: 'Masterserver offline', online: 'Online', loading: 'Bezig…',
      noServersOffline: 'De live serverlijst is nu niet bereikbaar. Het tabblad Servers in de launcher toont dezelfde lijst.',
      moreNotes: 'Toon alle notities', topAll: 'Altijd', top30: 'Laatste 30 dagen', cmpAdd: 'Vergelijk', cmpOn: 'Vergeleken', cmpTitle: 'Wapens vergelijken', cmpHint: 'Kies tot drie wapens om te vergelijken.', cmpClear: 'Wissen', cmpDmg: 'Schade per treffer', cmpRpm: 'Vuursnelheid', cmpDps: 'Schade per seconde', cmpMag: 'Magazijn', cmpEmpty: 'Tijd tot leeg', cmpReload: 'Volledig herladen', cmpPellets: 'hagels', cmpNote: 'Rompschoten, voor afstand en bepantsering. Bij hagelgeweren telt elke hagel mee.', lessNotes: 'Minder tonen', liveNow: '{p} spelers op {s} servers op dit moment', liveIdle: '{s} servers nu online',
      noServers: 'Er host nu niemand een publieke server. Host er zelf een vanuit de launcher met Openbaar tonen aan.',
      players: 'spelers', servers: 'servers', password: 'Wachtwoord', ranked: 'Ranked', unranked: 'Unranked', rankedTip: 'Potjes tellen mee voor de ranglijsten', need1: 'Zoekt 1 speler', needN: 'Zoekt {n} spelers', needTip: 'Er is iemand vertrokken tijdens het potje. Val nu in en je kunt deze match geen rating verliezen.', unrankedTip: 'Potjes tellen niet mee voor de ranglijsten', bot: 'bot', bots: 'bots', copy: 'Adres kopiëren', copied: 'Gekopieerd', verified: 'Geverifieerd', verifiedTip: 'Gecontroleerd door het TrueCombat: Platinum-team', eac: 'Anti-cheat', eacTip: 'Beschermd door Easy Anti-Cheat', eacReqTip: 'Beschermd door Easy Anti-Cheat. Verplicht om te joinen.', joinBtn: 'Joinen',
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
      matchReport: 'Wedstrijdverslag', matchOn: '{mode} op {map}', matchCopy: 'Link naar dit potje kopiëren', topWeapon: 'Beste wapen', map: 'Map', mode: 'Modus', length: 'Duur', server: 'Server', unknownMatch: 'Dit potje is niet gevonden.', viewMatch: 'Wedstrijdverslag', noTeam: 'Spelers', version: 'Versie',
      reads: '{n} keer gelezen', read1: '1 keer gelezen', ratingOf: '{avg} uit {n} beoordelingen', topRated: 'Best beoordeeld',
      statLeaders: 'Toppers per stat', statNote: 'Geverifieerde potjes met anti-cheat aan, alleen tegen echte spelers.', scopeAll: 'Alle geverifieerde', scopeRanked: 'Alleen ranked',
      allMaps: 'Alle maps', allModes: 'Alle modi', allWeapons: 'Alle wapens', p7: '7 dagen', p30: '30 dagen', pAll: 'Altijd', statPick: 'Stat',
      minSample: 'Toont spelers met minstens {n} {what}.', boardEmpty: 'Nog geen geverifieerde potjes voor deze keuze.', value: 'Waarde',
      secCombat: 'Gevecht', secPlay: 'Speelstijl', secObj: 'Doelen en rondes', secHits: 'Waar de treffers landen', secMaps: 'Maps', secModes: 'Modi',
      secRivals: 'Rivalen', secActivity: 'Activiteit', nemesis: 'Aartsvijand', nemesisTip: 'Schakelde deze speler het vaakst uit', victim: 'Favoriete doelwit',
      victimTip: 'Werd het vaakst door deze speler uitgeschakeld', h2h: 'Onderling', compareWith: 'Vergelijk met een andere speler', h2hKills: 'Kills op elkaar',
      h2hAgainst: 'Potjes als tegenstanders', h2hTogether: 'Potjes als teamgenoten', h2hWins: 'Winst tegen elkaar', head: 'Hoofd', body: 'Romp', legs: 'Benen',
      accNote: 'Trefzekerheid telt alleen potjes zonder bots. Trefferzones tellen elke treffer op een echte speler.', detailEmpty: 'Gedetailleerde statistieken starten met versie 0.35.0.',
      detailNote: 'Geteld uit geverifieerde potjes met anti-cheat aan, alleen tegen echte spelers. Bots, opwarmen en stilstaan tellen nooit mee.',
      kills_on: '{n} kills', perDay: '{n} potjes', less: 'Minder', more: 'Meer', matchesN: '{n} potjes', m: 'm',
      s_kills: 'Kills', s_deaths: 'Doden', s_assists: 'Assists', s_headshots: 'Headshotkills', s_damage: 'Schade gedaan', s_damageTaken: 'Schade opgelopen',
      s_kd: 'K/D', s_headshotRate: 'Headshotpercentage', s_accuracy: 'Trefzekerheid', s_headHitRate: 'Hoofdtreffers', s_adr: 'Schade per ronde', s_winRate: 'Winstpercentage',
      s_kpm: 'Kills per minuut', s_avgKillDistance: 'Gemiddelde killafstand', s_longestKill: 'Langste kill', s_bestStreak: 'Beste reeks',
      s_doubleKills: 'Dubbele kills', s_tripleKills: 'Driedubbele kills', s_quadKills: 'Viervoudige kills', s_openingKills: 'Openingskills', s_openingDeaths: 'Eerste gesneuveld',
      s_clutches: 'Clutches gewonnen', s_bestClutch: 'Beste clutch', s_trades: 'Tradekills', s_revenges: 'Wraakkills', s_knifeKills: 'Meskills',
      s_grenadeKills: 'Granaatkills', s_aimedKills: 'Kills met richten', s_hipKills: 'Kills vanuit de heup', s_standKills: 'Staand', s_crouchKills: 'Gehurkt',
      s_proneKills: 'Liggend', s_leanKills: 'Leunend', s_airKills: 'In de lucht', s_objectives: 'Doelen', s_captures: 'Vlaggen veroverd',
      s_plants: 'Bommen geplaatst', s_defuses: 'Bommen ontmanteld', s_returns: 'Vlaggen teruggebracht', s_roundsWon: 'Rondes gewonnen', s_roundMvps: 'Ronde-MVP', s_wins: 'Potjes gewonnen',
      s_matches: 'Potjes', s_timePlayed: 'Speeltijd', s_xp: 'Ervaring', s_shots: 'Schoten', s_hitsAll: 'Treffers',
      verified: 'Geverifieerd account', noProfile: 'Er is geen openbaar profiel met die naam.',
      acctLedeIn: 'Je bent aangemeld. Koppel elke pc waarop je speelt en je record gaat overal mee.', acctFree: 'Beschikbaar.', acctChecking: 'Bezig met controleren…',
      acctRenameIn: 'Je kunt je naam over {n} dagen opnieuw wijzigen.', acctRenameNow: 'Je kunt je naam één keer per 30 dagen wijzigen. Je oude naam blijft 30 dagen voor je vastgehouden.', acctNameFree: 'Je naam is na een jaar afwezigheid vrijgegeven en iemand anders heeft hem genomen. Kies hieronder een nieuwe.',
      acctPcs: '{n} van 8', acctLinkedOn: 'gekoppeld op {d}', acctUnlink: 'Ontkoppelen', acctSure: 'Deze pc ontkoppelen?', acctNoPcs: 'Nog geen pc gekoppeld. Open deze pagina op de pc waarop je speelt en kies Deze pc koppelen.',
      acctLinkOpen: 'Wachten op de launcher. Keur de koppeling daar goed. Gebeurt er niets? Werk de launcher bij en probeer opnieuw.',
      acctLinkDone: 'Deze pc is gekoppeld. Je record gaat nu overal mee.', acctLinkExpired: 'De koppelcode is verlopen. Kies Deze pc koppelen om opnieuw te proberen.',
      acctSigninFailed: 'Aanmelden is niet gelukt. Probeer het opnieuw.', acctSigninDiscord: 'Discord gaf geen antwoord. Probeer het over een minuut opnieuw.',
      acctSigninSlow: 'Te veel aanmeldingen vanaf hier. Wacht een paar minuten.', acctOnDiscord: 'op Discord'
    }
  };
  /* German, French and Polish strings arrive in js/lang-<code>.js (window.TCP_L); English fills any gap */
  var L = Object.assign({}, DICT.en, DICT[lang] || window.TCP_L || {});

  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmtDate(iso) { var d = new Date(iso); return d.getUTCDate() + ' ' + L.months[d.getUTCMonth()] + ' ' + d.getUTCFullYear(); }
  function inline(t) { return esc(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>'); }
  function $all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  var CHEV = ' <svg class="chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';

  /* mobile menu closes after a pick */
  var menu = document.getElementById('menu');
  if (menu) menu.addEventListener('click', function (e) { if (e.target.tagName === 'A') menu.open = false; });
  /* ...and on Escape or a click outside it, handing focus back to the menu button */
  if (menu) {
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && menu.open) { menu.open = false; var sm = menu.querySelector('summary'); if (sm) sm.focus(); } });
    document.addEventListener('click', function (e) { if (menu.open && !menu.contains(e.target)) menu.open = false; });
  }

  /* language menu closes on a click elsewhere or Escape */
  var langs = document.querySelector('.nav-langs');
  if (langs) {
    document.addEventListener('click', function (e) { if (langs.open && !langs.contains(e.target)) langs.open = false; });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') langs.open = false; });
  }

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
    var meta = (n.num ? '#' + esc(n.num) + ' · ' : '') + esc(n.build || rel.tag_name) + ' · ' + fmtDate(rel.published_at);
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
    /* release pages exist only once the site has been rebuilt for that version: keep the links the static HTML has */
    var pages = {};
    $all('.rel-page', box).forEach(function (p) { var d = p.closest('.release'); if (d) pages[d.dataset.ver] = p.outerHTML; });
    var older = $all('.release[data-ver]', box).filter(function (d) { return !seen[d.dataset.ver]; });
    older.forEach(function (d) { d.open = false; var b = d.querySelector('.latest'); if (b) b.remove(); });
    box.innerHTML = html;
    $all('.release[data-ver]', box).forEach(function (d) { var b = d.querySelector('.body'); if (b && pages[d.dataset.ver] && !b.querySelector('.rel-page')) b.insertAdjacentHTML('beforeend', pages[d.dataset.ver]); });
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
    return name ? '<a href="maps#' + name.toLowerCase() + '">' + name + '</a>' : esc(m);
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
  /* Easy Anti-Cheat badge: the bridge reports eac 0 (off), 1 (on) or 2 (required); nothing is shown while it is off */
  function eacTag(s) { return s && s.eac > 0 ? ' <span class="srv-tag eac" title="' + (s.eac > 1 ? L.eacReqTip : L.eacTip) + '">' + L.eac + '</span>' : ''; }
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
        (s.verified ? ' <span class="srv-tag verified" title="' + L.verifiedTip + '">' + L.verified + '</span>' : '') +
        eacTag(s) +
        '<button type="button" class="addr" data-addr="' + esc(s.address) + '" title="' + L.copy + '">' + esc(s.address) + '</button>' +
        ' <a class="srv-join" href="' + (lang === 'en' ? '' : '../') + 'join#' + esc(s.address) + '">' + L.joinBtn + '</a></td>' +
        '<td>' + mapLabel(s.map) + '</td><td>' + (s.players || 0) + ' / ' + (s.maxPlayers || '?') + (s.bots ? ' <span class="srv-bots">+' + s.bots + ' ' + (s.bots === 1 ? L.bot : L.bots) + '</span>' : '') + '</td><td>' + esc(s.mode || '') + '</td></tr>';
    }).join('');
    renderBoards(list);
    var upd = root.querySelector('.srv-updated');
    if (upd && data.updated) { upd.textContent = L.updated + ' ' + new Date(data.updated).toLocaleTimeString(lang, { hour: '2-digit', minute: '2-digit' }); upd.hidden = false; }
  }
  /* live scoreboards for every server with someone on it (servers page) */
  var IMG = (lang === 'en' ? '' : '../') + 'img/';
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
        '<div><h3>' + esc(shortName(s.name)) + eacTag(s) + '</h3><p>' + mapLabel(s.map) + ' · ' + esc(s.mode || '') + '</p></div>' +
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

  var MID = /^[0-9a-f]{16}$/;
  function matchHref(id) { return 'match?id=' + encodeURIComponent(id); }

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
          var mvp = m.mvp ? '<span class="mvp"><b>' + L.mvp + '</b> <a href="' + esc(profileHref(m.mvp.id)) + '">' + esc(m.mvp.name) + '</a> · ' + num(m.mvp.kills) + ' ' + L.kills.toLowerCase() + '</span>' : '';
          return '<li><img src="' + art + '" alt="" width="120" height="68" loading="lazy"><div class="r-main"><p class="r-top">' + (MID.test(m.id || '') ? '<a href="' + matchHref(m.id) + '"><b>' + mapLabel(m.map) + '</b></a>' : '<b>' + mapLabel(m.map) + '</b>') + res + '</p><p class="r-sub">' + bits + '</p></div>' +
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
  /* official server cards are static HTML; they get the anti-cheat badge once the live list reports it on */
  if (document.querySelector('.official .addr')) api('/servers.json').then(function (d) {
    var list = d.servers || [];
    $all('.official article').forEach(function (card) {
      var b = card.querySelector('.addr'), port = b && b.dataset.addr.split(':').pop();
      var s = list.filter(function (x) { return String(x.address).split(':').pop() === port && (x.verified || /official/i.test(x.name || '')); })[0];
      var tag = eacTag(s), first = card.querySelector('.srv-tag');
      if (!tag || !first || card.querySelector('.srv-tag.eac')) return;
      var row = document.createElement('span'); row.className = 'srv-tags';
      first.parentNode.insertBefore(row, first); row.appendChild(first); row.insertAdjacentHTML('beforeend', tag);
    });
  }, function () {});
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
  function num(n) { return (Number(n) || 0).toLocaleString(lang); }
  function pct(n) { return Math.round((n || 0) * 100) + '%'; }
  function badge(r) { return r ? '<span class="badge" title="' + esc(r.title) + '">' + esc(r.short) + '</span>' : ''; }
  function dur(s) { var h = Math.floor((s || 0) / 3600), m = Math.round(((s || 0) % 3600) / 60); return h ? h + ' ' + L.hours + ' ' + m + ' ' + L.minutes : m + ' ' + L.minutes; }
  function kdOf(p) { return p.deaths ? p.kills / p.deaths : (p.kills || 0); }
  function profileHref(id) { return 'player?id=' + encodeURIComponent(id); }
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

  /* ---------- optional player accounts (same origin: truecombat.eu/api/account) ----------
     Everything here stays quiet while the account service is not running: the profile and leaderboards
     look exactly as before, and the account page says accounts open with the next update. */
  var ACCT = '/api/account';
  function acctFetch(path, opts) {
    return fetch(ACCT + path, Object.assign({ credentials: 'same-origin', cache: 'no-store' }, opts || {})).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (d) {
        if (!r.ok) { var e = new Error(d.error || ('HTTP ' + r.status)); e.status = r.status; throw e; }
        return d;
      });
    });
  }
  var TICK = '<svg class="acct-tick" width="14" height="14" viewBox="0 0 24 24" role="img" aria-label="' + esc(L.verified) + '"><title>' + esc(L.verified) +
    '</title><circle cx="12" cy="12" r="11" fill="currentColor"/><path d="M7 12.5l3.2 3.2L17 9" fill="none" stroke="#0d1016" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  function profileUrl(name) { return 'player?u=' + encodeURIComponent(name); }
  var acctNamesP = null;
  function acctNames() {   // stats id -> account name of every public account
    if (!acctNamesP) acctNamesP = fetch(ACCT + '/names.json').then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).catch(function () { return {}; });
    return acctNamesP;
  }
  /* links to a profile by id show the account name with a tick, and lead to the short profile address */
  if (document.querySelector('[data-leaderboard],[data-top],[data-recent],[data-servers],[data-player],[data-match],[data-statboard],[data-pf-detail]')) {
    acctNames().then(function (names) {
      if (!Object.keys(names).length) return;
      var busy = false;
      function decorate() {
        busy = false;
        $all('a[href^="player?id="]:not([data-acct-done])').forEach(function (a) {
          a.setAttribute('data-acct-done', '');
          var id = (a.getAttribute('href').split('id=')[1] || '').split('&')[0];
          var name = names[id];
          if (!name) return;
          a.textContent = name;
          a.setAttribute('href', profileUrl(name));
          a.insertAdjacentHTML('beforeend', ' ' + TICK);
        });
      }
      decorate();
      if (window.MutationObserver) new MutationObserver(function () { if (!busy) { busy = true; requestAnimationFrame(decorate); } }).observe(document.body, { childList: true, subtree: true });
    });
  }
  /* the player page: player?u=<account name> or player?id=<stats id> */
  var PROFILE = new Promise(function (done) {
    var sp = new URLSearchParams(location.search), id = (sp.get('id') || '').toLowerCase(), u = sp.get('u') || '';
    if (!u) return done({ id: id, acct: null });
    acctFetch('/profile?u=' + encodeURIComponent(u)).then(function (a) { done({ id: a.statsId, acct: a }); },
      function () { done({ id: '', acct: null, missing: true }); });
  });

  $all('[data-account]').forEach(function (root) {
    function q(sel) { return root.querySelector(sel); }
    var me = null, poll = null;
    function show(which) { ['out', 'signup', 'in', 'off'].forEach(function (k) { q('[data-acct-' + k + ']').hidden = k !== which; }); }
    function post(path, body) {
      return acctFetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF': (me && me.csrf) || '' }, body: JSON.stringify(body || {}) });
    }
    function err(sel, e) { var el = q(sel); el.textContent = e ? (e.message || String(e)) : ''; el.hidden = !e; }
    function render(d) {
      me = d;
      if (!d.signedIn) {
        show('out');
        var why = { failed: L.acctSigninFailed, discord: L.acctSigninDiscord, slow: L.acctSigninSlow }[new URLSearchParams(location.search).get('signin') || ''];
        if (why) q('[data-acct-lede]').textContent = why;
        return;
      }
      if (d.needsSignup) { show('signup'); q('[data-acct-as]').textContent = (d.discord && d.discord.name) || ''; return; }
      var a = d.account;
      show('in');
      q('[data-acct-title]').innerHTML = esc(a.name) + ' ' + TICK;
      q('[data-acct-lede]').textContent = L.acctLedeIn;
      q('[data-acct-name]').textContent = a.name;
      var prof = q('[data-acct-profile]');
      prof.href = profileUrl(a.name);
      prof.hidden = a.visibility !== 'public';
      q('[data-acct-rename] input').placeholder = a.name;
      q('[data-acct-rename-note]').textContent = a.nameReserved === false ? L.acctNameFree : a.nameChangeIn > 0 ? L.acctRenameIn.replace('{n}', Math.ceil(a.nameChangeIn / 86400)) : L.acctRenameNow;
      q('[data-acct-public]').checked = a.visibility === 'public';
      q('[data-acct-discord]').checked = !!a.showDiscord;
      var keys = (a.keys || []).filter(function (k) { return !k.retired; });
      q('[data-acct-pcs]').textContent = L.acctPcs.replace('{n}', keys.length);
      q('[data-acct-keys]').innerHTML = keys.length ? keys.map(function (k) {
        return '<li><b>' + esc(k.label || 'PC') + '</b> <span class="muted">' + L.acctLinkedOn.replace('{d}', fmtDate(new Date(k.linked * 1000).toISOString())) +
          ' · ' + esc(k.id.slice(0, 8)) + '</span><button type="button" class="btn" data-unlink="' + esc(k.id) + '">' + L.acctUnlink + '</button></li>';
      }).join('') : '<li class="muted">' + L.acctNoPcs + '</li>';
    }
    function refresh() { return acctFetch('/me').then(render, function () { show('off'); }); }
    refresh();

    var form = q('[data-acct-signup-form]'), timer = null;
    form.name.addEventListener('input', function () {
      clearTimeout(timer);
      var v = form.name.value.trim(), hint = q('[data-acct-check]');
      if (v.length < 3) return;
      hint.textContent = L.acctChecking;
      timer = setTimeout(function () {
        acctFetch('/check?name=' + encodeURIComponent(v)).then(function (r) { hint.textContent = r.ok ? L.acctFree : r.reason; hint.classList.toggle('bad', !r.ok); }, function () {});
      }, 350);
    });
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      err('[data-acct-error]', null);
      post('/signup', { name: form.name.value, visibility: form.visibility.value, age13: form.age13.checked }).then(render, function (x) { err('[data-acct-error]', x); });
    });
    q('[data-acct-rename]').addEventListener('submit', function (e) {
      e.preventDefault();
      err('[data-acct-rename-error]', null);
      post('/name', { name: e.target.name.value }).then(function (d) { e.target.reset(); render(d); }, function (x) { err('[data-acct-rename-error]', x); });
    });
    q('[data-acct-public]').addEventListener('change', function (e) { post('/settings', { visibility: e.target.checked ? 'public' : 'hidden' }).then(render, refresh); });
    q('[data-acct-discord]').addEventListener('change', function (e) { post('/settings', { showDiscord: e.target.checked }).then(render, refresh); });
    q('[data-acct-link]').addEventListener('click', function () {
      var state = q('[data-acct-link-state]');
      clearInterval(poll);
      post('/link/start').then(function (r) {
        state.textContent = L.acctLinkOpen; state.hidden = false;
        location.href = r.url;
        var until = Date.now() + r.expires_in * 1000;
        poll = setInterval(function () {
          if (document.hidden) return;
          acctFetch('/link/status?code=' + r.code).then(function (s) {
            if (s.state === 'linked') { clearInterval(poll); state.textContent = L.acctLinkDone; refresh(); }
            else if (s.state === 'expired' || Date.now() > until) { clearInterval(poll); state.textContent = L.acctLinkExpired; }
          }, function () {});
        }, 2000);
      }, function (x) { state.textContent = x.message; state.hidden = false; });
    });
    q('[data-acct-keys]').addEventListener('click', function (e) {
      var b = e.target.closest('[data-unlink]');
      if (!b) return;
      if (!b.classList.contains('sure')) { b.classList.add('sure'); b.textContent = L.acctSure; return; }
      post('/unlink', { key: b.dataset.unlink }).then(render, refresh);
    });
    q('[data-acct-signout]').addEventListener('click', function () { post('/logout').then(function () { location.replace('account'); }, function () {}); });
    q('[data-acct-delete]').addEventListener('submit', function (e) {
      e.preventDefault();
      err('[data-acct-delete-error]', null);
      post('/delete', { confirm: e.target.confirm.value }).then(function () { location.replace('./'); }, function (x) { err('[data-acct-delete-error]', x); });
    });
  });

  /* ---------- player profile page ---------- */
  $all('[data-player]').forEach(function (root) {
    function q(sel) { return root.querySelector(sel); }
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
    PROFILE.then(function (pr) {
    var id = pr.id, acct = pr.acct;
    if (pr.missing) { missing(L.noProfile); return; }
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
      box.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(L.rating) + ': ' + Math.round(pts[0]) + ' → ' + Math.round(+p.rating || 0) + '">' +
        '<path d="' + area + '" class="area"/><polyline points="' + line + '" class="line"/>' + dots + '</svg>' +
        '<div class="pf-scale"><span>' + Math.round(hi) + '</span><span>' + Math.round(lo) + '</span></div>';
    }

    api('/player.json?id=' + id).then(function (p) {
      var r = p.rank || {};
      document.title = (acct ? acct.name : p.name) + ' · ' + L.profile + ' · TrueCombat: Platinum';
      q('[data-pf-name]').textContent = p.name;
      if (acct) {
        q('[data-pf-name]').innerHTML = esc(acct.name) + ' ' + TICK;
        if (acct.discord && acct.discord.name) {
          q('[data-pf-name]').insertAdjacentHTML('afterend', '<p class="acct-discord-line">' + (acct.discord.avatar ? '<img src="' + esc(acct.discord.avatar) +
            '" alt="" width="22" height="22" loading="lazy">' : '') + '<span>' + esc(acct.discord.name) + '</span> <span class="muted">' + L.acctOnDiscord + '</span></p>');
        }
      } else {
        acctNames().then(function (names) {      // an account's own id: show its name and move to the short address
          if (!names[id]) return;
          q('[data-pf-name]').innerHTML = esc(names[id]) + ' ' + TICK;
          try { history.replaceState(null, '', profileUrl(names[id])); } catch (e) {}
        });
      }
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
        return '<tr><td>' + (MID.test(m.id || '') ? '<a href="' + matchHref(m.id) + '">' + fmtDate(m.ended) + '</a>' : fmtDate(m.ended)) + '</td><td>' + mapLabel(m.map) + '</td><td>' + esc(m.mode || '') + '</td><td class="' + (m.won ? 'up' : 'down') + '">' +
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
  });

  /* ---------- detailed stats (tcp-match/2): stat leaders and the full profile ---------- */
  var STAT_ORDER = ['kills', 'kd', 'headshotRate', 'accuracy', 'adr', 'assists', 'damage', 'wins', 'winRate', 'kpm', 'longestKill', 'avgKillDistance',
    'bestStreak', 'openingKills', 'clutches', 'trades', 'revenges', 'doubleKills', 'tripleKills', 'quadKills', 'knifeKills', 'grenadeKills', 'aimedKills',
    'hipKills', 'crouchKills', 'proneKills', 'leanKills', 'airKills', 'objectives', 'plants', 'defuses', 'captures', 'returns', 'roundMvps', 'roundsWon',
    'headshots', 'matches', 'timePlayed', 'xp'];
  var PCT = { headshotRate: 1, accuracy: 1, headHitRate: 1, winRate: 1 };
  var DIST = { longestKill: 1, avgKillDistance: 1 };
  function sLabel(k) { return L['s_' + k] || k; }
  function sVal(k, v) {
    if (v == null) return '–';
    if (PCT[k]) return (Math.round(v * 10) / 10).toLocaleString(lang) + '%';
    if (DIST[k]) return Math.round(v).toLocaleString(lang) + ' ' + L.m;
    if (k === 'timePlayed') return dur(v);
    if (k === 'kd' || k === 'kpm') return (+v).toFixed(2);
    if (k === 'adr') return Math.round(v).toLocaleString(lang);
    if (k === 'bestClutch') return '1v' + num(v);
    return num(v);
  }
  function seg(name, opts, cur) {
    return '<div class="tabs" role="group" aria-label="' + esc(name) + '">' + opts.map(function (o) {
      return '<button type="button" data-v="' + esc(o[0]) + '" aria-pressed="' + (o[0] === cur) + '">' + esc(o[1]) + '</button>';
    }).join('') + '</div>';
  }

  $all('[data-statboard]').forEach(function (root) {
    var st = { stat: 'kills', period: 'all', scope: 'all', map: '', mode: '', weapon: '' };
    function sel(key, first, list, label) {
      return '<label class="sb-sel"><span class="sr-only">' + esc(label) + '</span><select data-k="' + key + '"><option value="">' + esc(first) + '</option>' +
        list.map(function (o) { return '<option value="' + esc(o[0]) + '"' + (st[key] === o[0] ? ' selected' : '') + '>' + esc(o[1]) + '</option>'; }).join('') + '</select></label>';
    }
    root.innerHTML = '<header><h2>' + L.statLeaders + '</h2><span class="pill">' + L.loading + '</span></header>' +
      '<div class="lb-tools sb-tools">' +
      sel('stat', sLabel('kills'), STAT_ORDER.slice(1).map(function (k) { return [k, sLabel(k)]; }), L.statPick) +
      '<div data-seg="scope">' + seg(L.scopeAll, [['all', L.scopeAll], ['ranked', L.scopeRanked]], 'all') + '</div>' +
      '<div data-seg="period">' + seg(L.played, [['all', L.pAll], ['30d', L.p30], ['7d', L.p7]], 'all') + '</div>' +
      '<span class="sb-meta"></span></div><div class="table-scroll"><table class="srv-table lb-table"><thead><tr><th>#</th><th>' + L.player + '</th><th data-sb-head>' + sLabel('kills') +
      '</th></tr></thead><tbody></tbody></table></div><p class="srv-empty" hidden></p><p class="yt-note sb-note"></p>';
    var tbody = root.querySelector('tbody'), empty = root.querySelector('.srv-empty'), note = root.querySelector('.sb-note');
    root.querySelector('select[data-k="stat"] option').value = 'kills';
    api('/statmeta.json').then(function (m) {
      root.querySelector('.sb-meta').outerHTML =
        ((m.maps || []).length > 1 ? sel('map', L.allMaps, m.maps.map(function (x) { return [x, MAPS[String(x).toLowerCase()] || x]; }), L.map) : '') +
        ((m.modes || []).length > 1 ? sel('mode', L.allModes, m.modes.map(function (x) { return [x, x]; }), L.mode) : '') +
        ((m.weapons || []).length ? sel('weapon', L.allWeapons, m.weapons.map(function (x) { return [x, x]; }), L.weapons) : '');
    }, function () {});
    function load() {
      var qs = '/statboard.json?limit=100&stat=' + st.stat + '&period=' + st.period + '&scope=' + st.scope +
        (st.map ? '&map=' + encodeURIComponent(st.map) : '') + (st.mode ? '&mode=' + encodeURIComponent(st.mode) : '') + (st.weapon ? '&weapon=' + encodeURIComponent(st.weapon) : '');
      root.querySelector('[data-sb-head]').textContent = sLabel(st.stat);
      api(qs).then(function (d) {
        setPill(root, true, L.statNote);
        root.querySelector('[data-sb-head]').textContent = sLabel(d.stat || st.stat);
        var rows = d.players || [];
        note.textContent = d.minimum ? L.minSample.replace('{n}', num(d.minimum.value)).replace('{what}', (d.minimum.stat === 'timePlayed' ? L.minutes : sLabel(d.minimum.stat)).toLowerCase()) : '';
        if (d.minimum && d.minimum.stat === 'timePlayed') note.textContent = L.minSample.replace('{n}', num(d.minimum.value / 60)).replace('{what}', L.minutes);
        empty.textContent = L.boardEmpty; empty.hidden = rows.length > 0;
        tbody.innerHTML = rows.map(function (p) {
          return '<tr><td class="rank">' + num(p.position) + '</td><td><a class="who" href="' + esc(profileHref(p.id)) + '">' + esc(p.name) + '</a></td><td>' + sVal(d.stat || st.stat, p.value) + '</td></tr>';
        }).join('');
      }, function () { setPill(root, false, TCP_API ? L.offline : L.soon); empty.textContent = L.lbOffline; empty.hidden = false; tbody.innerHTML = ''; });
    }
    root.addEventListener('change', function (e) { var k = e.target.dataset && e.target.dataset.k; if (k) { st[k] = e.target.value || (k === 'stat' ? 'kills' : ''); load(); } });
    root.addEventListener('click', function (e) {
      var b = e.target.closest('[data-seg] button'); if (!b) return;
      var g = b.closest('[data-seg]'); $all('button', g).forEach(function (o) { o.setAttribute('aria-pressed', String(o === b)); });
      st[g.dataset.seg] = b.dataset.v; load();
    });
    load();
  });

  $all('[data-pf-detail]').forEach(function (box) {
    PROFILE.then(function (pr) {
    var id = pr.id;
    if (!PID.test(id) || !TCP_API) return;
    var scope = 'all';
    function tiles(t, keys) {
      return '<div class="pf-stats sd-tiles">' + keys.map(function (k) {
        var sub = k === 'kd' ? num(t.kills) + ' / ' + num(t.deaths) : k === 'accuracy' ? num(t.hits) + ' / ' + num(t.shots) : k === 'bestClutch' && t.clutches ? sVal('clutches', t.clutches) + ' ' + sLabel('clutches').toLowerCase() : '';
        return '<div><span>' + sLabel(k) + '</span><b>' + sVal(k, t[k]) + '</b>' + (sub ? '<small>' + sub + '</small>' : '') + '</div>';
      }).join('') + '</div>';
    }
    function card(title, inner, cls) { return '<div class="server-card full sd-card ' + (cls || '') + '"><header><h2>' + title + '</h2></header>' + inner + '</div>'; }
    function bars(t, keys) {
      var total = keys.reduce(function (s, k) { return s + (t[k] || 0); }, 0) || 1;
      return '<ul class="sd-bars">' + keys.map(function (k) {
        var v = t[k] || 0;
        return '<li><span>' + (L[k] || sLabel(k)) + '</span><b>' + num(v) + '</b><i style="--w:' + (v / total * 100).toFixed(1) + '%"></i><em>' + Math.round(v / total * 100) + '%</em></li>';
      }).join('') + '</ul>';
    }
    function table(rows, head) {
      return '<div class="table-scroll"><table class="srv-table"><thead><tr><th>' + head + '</th><th>' + L.matches.charAt(0).toUpperCase() + L.matches.slice(1) + '</th><th>' + L.winRate +
        '</th><th>' + L.kd + '</th><th>' + L.played + '</th></tr></thead><tbody>' + (rows.map(function (r) {
          return '<tr><td><b>' + (head === L.map ? mapLabel(r.name) : esc(r.name || '–')) + '</b></td><td>' + num(r.matches) + '</td><td>' + sVal('winRate', r.winRate) + '</td><td>' +
            (+r.kd).toFixed(2) + '</td><td>' + dur(r.timePlayed) + '</td></tr>';
        }).join('') || '<tr><td colspan="5">–</td></tr>') + '</tbody></table></div>';
    }
    function rival(r, label, tip) {
      if (!r) return '<div class="sd-rival"><span>' + label + '</span><b>–</b></div>';
      return '<div class="sd-rival" title="' + esc(tip) + '"><span>' + label + '</span><b><a href="' + esc(profileHref(r.id)) + '">' + esc(r.name) + '</a></b><small>' +
        L.kills_on.replace('{n}', num(r.kills)) + ' · <a href="#h2h" data-h2h="' + esc(r.id) + '">' + L.h2h + '</a></small></div>';
    }
    function calendar(days) {
      var map = {}; (days || []).forEach(function (d) { map[d.day] = d.matches; });
      var today = new Date(), start = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate() - 364));
      start.setUTCDate(start.getUTCDate() - ((start.getUTCDay() + 6) % 7));
      var cells = '';
      for (var d = new Date(start); d <= today; d.setUTCDate(d.getUTCDate() + 1)) {
        var k = d.toISOString().slice(0, 10), n = map[k] || 0, lvl = n ? Math.min(4, Math.ceil(n / 2)) : 0;
        cells += '<i class="l' + lvl + '" title="' + esc(fmtDate(k) + ' · ' + L.perDay.replace('{n}', n)) + '"></i>';
      }
      return '<div class="table-scroll"><div class="sd-cal" role="img" aria-label="' + esc(L.secActivity) + '">' + cells + '</div></div>' +
        '<p class="sd-legend"><span>' + L.less + '</span><i class="l0"></i><i class="l1"></i><i class="l2"></i><i class="l3"></i><i class="l4"></i><span>' + L.more + '</span></p>';
    }
    function h2hPanel() {
      return '<div class="server-card full sd-card" id="h2h"><header><h2>' + L.h2h + '</h2></header><form class="lb-search sd-h2h-find" role="search"><input type="search" name="q" minlength="2" maxlength="36" placeholder="' +
        esc(L.compareWith) + '" aria-label="' + esc(L.compareWith) + '"></form><ul class="sd-h2h-list"></ul><div class="sd-h2h-out"></div></div>';
    }
    function showH2h(other) {
      var out = box.querySelector('.sd-h2h-out');
      api('/h2h.json?a=' + id + '&b=' + other + '&scope=' + scope).then(function (h) {
        function side(p) { return '<div><a href="' + esc(profileHref(p.id)) + '">' + esc(p.name) + '</a><b>' + num(p.kills) + '</b><small>' + num(p.wins) + ' ' + L.wins.toLowerCase() + '</small></div>'; }
        out.innerHTML = '<div class="sd-vs">' + side(h.a) + '<span>' + L.h2hKills + '</span>' + side(h.b) + '</div><p class="muted">' + L.h2hAgainst + ': ' + num(h.matchesAgainst) +
          ' · ' + L.h2hTogether + ': ' + num(h.matchesTogether) + '</p>' + (h.recent || []).map(function (m) {
            return '<a class="sd-h2h-m" href="' + matchHref(m.id) + '">' + fmtDate(m.ended) + ' · ' + mapLabel(m.map) + ' · ' + esc(m.mode || '') + '</a>';
          }).join('');
      }, function () { out.innerHTML = '<p class="muted">' + L.unknownPlayer + '</p>'; });
    }
    function draw(d) {
      var t = d.totals || {};
      if (d.removed) { box.innerHTML = ''; return; }
      if (!t.matches) { box.innerHTML = '<p class="yt-note">' + L.detailEmpty + '</p>'; return; }
      box.innerHTML =
        '<div class="sd-top"><div data-seg="scope">' + seg(L.scopeAll, [['all', L.scopeAll], ['ranked', L.scopeRanked]], scope) + '</div><p class="yt-note">' + L.detailNote + '</p></div>' +
        card(L.secCombat, tiles(t, ['kd', 'adr', 'headshotRate', 'accuracy', 'assists', 'kpm', 'longestKill', 'avgKillDistance', 'bestStreak', 'openingKills', 'clutches', 'bestClutch',
          'trades', 'revenges', 'doubleKills', 'tripleKills', 'quadKills', 'damageTaken'])) +
        card(L.secHits, bars({ head: t.hitsHead, body: t.hitsBody, legs: t.hitsLegs }, ['head', 'body', 'legs']) + '<p class="yt-note">' + L.accNote + '</p>', 'sd-half') +
        card(L.secPlay, bars(t, ['aimedKills', 'hipKills']) + bars(t, ['standKills', 'crouchKills', 'proneKills']) +
          tiles(t, ['leanKills', 'airKills', 'knifeKills', 'grenadeKills']), 'sd-half') +
        card(L.secObj, tiles(t, ['objectives', 'plants', 'defuses', 'captures', 'returns', 'roundsWon', 'roundMvps', 'openingDeaths'])) +
        card(L.secMaps, table(d.maps || [], L.map), 'sd-half') + card(L.secModes, table(d.modes || [], L.mode), 'sd-half') +
        card(L.secRivals, '<div class="sd-rivals">' + rival(d.nemesis, L.nemesis, L.nemesisTip) + rival(d.favouriteVictim, L.victim, L.victimTip) + '</div>', 'sd-half') +
        card(L.secActivity, calendar(d.activity), 'sd-half') + h2hPanel();
      var form = box.querySelector('.sd-h2h-find'), list = box.querySelector('.sd-h2h-list'), timer = null;
      function find() {
        var term = form.q.value.trim(); if (term.length < 2) { list.innerHTML = ''; return; }
        api('/search.json?q=' + encodeURIComponent(term)).then(function (r) {
          list.innerHTML = (r.players || []).filter(function (p) { return p.id !== id; }).slice(0, 6).map(function (p) {
            return '<li><button type="button" data-h2h="' + esc(p.id) + '">' + esc(p.name) + '</button></li>'; }).join('');
        }, function () {});
      }
      form.addEventListener('submit', function (e) { e.preventDefault(); find(); });
      form.q.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(find, 300); });
    }
    function load() { api('/stats.json?id=' + id + '&scope=' + scope).then(draw, function () { box.innerHTML = ''; }); }
    box.addEventListener('click', function (e) {
      var h = e.target.closest('[data-h2h]');
      if (h) { e.preventDefault(); box.querySelector('.sd-h2h-list').innerHTML = ''; showH2h(h.dataset.h2h); box.querySelector('#h2h').scrollIntoView({ behavior: 'smooth', block: 'start' }); return; }
      var b = e.target.closest('[data-seg] button'); if (b && b.dataset.v !== scope) { scope = b.dataset.v; load(); }
    });
    load();
    });
  });

  /* ---------- devlog: a dot on the nav link while the newest post is recent and unread ---------- */
  $all('a[data-devlog-new]').forEach(function (a) {
    var newest = a.dataset.devlogNew, seen = '';
    try {
      if (/(^|\/)devlog(-[^/]*)?\.html$|\/devlog(-[^/]*)?$/.test(location.pathname)) localStorage.setItem('tcp-devlog-seen', newest);
      seen = localStorage.getItem('tcp-devlog-seen') || '';
    } catch (e) {}
    var age = (Date.now() - new Date(newest + 'T00:00:00Z').getTime()) / 86400000;
    if (age < 14 && seen < newest) a.classList.add('fresh');
  });

  /* ---------- match report (match?id=<match id>) ---------- */
  $all('[data-match]').forEach(function (root) {
    function q(sel) { return root.querySelector(sel); }
    var id = (new URLSearchParams(location.search).get('id') || '').toLowerCase();
    function missing(text) { q('[data-m-missing-text]').textContent = text; q('[data-m-missing]').hidden = false; q('[data-m-lede]').hidden = true; }
    if (!id) return;
    $all('a[hreflang]').forEach(function (a) { a.href = a.getAttribute('href').split('?')[0] + '?id=' + id; });
    if (!MID.test(id)) { missing(L.unknownMatch); return; }
    if (!TCP_API) { missing(L.apiOffline); return; }
    api('/match.json?id=' + id).then(function (m) {
      var name = MAPS[String(m.map || '').toLowerCase()] || m.map || '';
      var w = String(m.winner || '').toLowerCase();
      var title = L.matchOn.replace('{mode}', m.mode || L.matchReport).replace('{map}', name);
      document.title = title + ' · ' + fmtDate(m.ended) + ' · TrueCombat: Platinum';
      q('[data-m-title]').textContent = title;
      var art = MAPS[String(m.map || '').toLowerCase()];
      if (art) { var a = q('[data-m-art]'); a.style.setProperty('--art', 'url(' + IMG + 'map-' + art.toLowerCase() + '.webp)'); a.style.setProperty('--art-s', 'url(' + IMG + 'map-' + art.toLowerCase() + '-640.webp)'); }
      var mins = Math.max(1, Math.round((m.duration || 0) / 60));
      q('[data-m-lede]').innerHTML = '<time datetime="' + esc(m.ended) + '">' + fmtDate(m.ended) + '</time>' + (m.server ? ' · ' + esc(shortName(m.server)) : '');

      var teams = ['specops', 'terrorists'].filter(function (t) { return (m.players || []).some(function (p) { return p.team === t; }); });
      var sc = m.score || {};
      var score = '';
      if (teams.length === 2) {
        score = '<div class="m-side specops' + (w === 'specops' ? ' won' : '') + '"><span>' + L.specops + '</span><b>' + num(sc.specops) + '</b></div>' +
          '<div class="m-mid">' + (w ? '<span class="res ' + esc(w) + '">' + L.wins_.replace('{t}', L[w] || esc(w)) + '</span>' : '<span class="res">' + L.draw + '</span>') + '</div>' +
          '<div class="m-side terrorists' + (w === 'terrorists' ? ' won' : '') + '"><b>' + num(sc.terrorists) + '</b><span>' + L.terrorists + '</span></div>';
      }
      var mvp = m.mvp ? '<p class="m-mvp"><b>' + L.mvp + '</b> <a href="' + esc(profileHref(m.mvp.id)) + '">' + esc(m.mvp.name) + '</a> · ' + num(m.mvp.kills) + ' ' + L.kills.toLowerCase() + '</p>' : '';
      q('[data-m-score]').innerHTML = (score ? '<div class="m-line">' + score + '</div>' : '') + mvp;

      var tiles = [[L.map, esc(name)], [L.mode, esc(m.mode || '–')], [L.length, mins + ' ' + L.minutes], [L.rounds, num(m.rounds)], [L.players, num((m.players || []).length)]];
      q('[data-m-facts]').innerHTML = tiles.map(function (t) { return '<div><span>' + t[0].charAt(0).toUpperCase() + t[0].slice(1) + '</span><b>' + t[1] + '</b></div>'; }).join('');

      function table(label, cls, list) {
        var rows = list.map(function (p) {
          var c = p.ratingChange || 0;
          return '<tr><td><a href="' + esc(profileHref(p.id)) + '">' + esc(p.name) + '</a>' + (m.mvp && m.mvp.id === p.id ? ' <span class="res">' + L.mvp + '</span>' : '') + '</td><td>' + num(p.kills) + '</td><td>' + num(p.deaths) +
            '</td><td>' + num(p.headshots) + '</td><td>' + num(p.damage) + '</td><td>' + num(p.objectives) + '</td><td>' + esc(p.topWeapon || '–') + '</td><td>+' + num(p.xp) +
            '</td><td class="' + (c > 0 ? 'up' : c < 0 ? 'down' : '') + '">' + (c > 0 ? '+' : '') + c + '</td></tr>';
        }).join('');
        return '<div class="server-card full m-team ' + cls + '"><header><h2>' + label + '</h2><span class="pill">' + list.length + ' ' + L.players + '</span></header><div class="table-scroll"><table class="srv-table">' +
          '<thead><tr><th>' + L.player + '</th><th>' + L.kills + '</th><th>' + L.deaths + '</th><th>HS</th><th>' + L.damage + '</th><th>' + L.objectives + '</th><th>' + L.topWeapon + '</th><th>XP</th><th>' + L.rating + '</th></tr></thead><tbody>' +
          rows + '</tbody></table></div></div>';
      }
      var html = teams.map(function (t) { return table(L[t], t, m.players.filter(function (p) { return p.team === t; })); }).join('');
      var rest = (m.players || []).filter(function (p) { return teams.indexOf(p.team) < 0; });
      if (rest.length) html += table(L.noTeam, '', rest);
      q('[data-m-teams]').innerHTML = html;

      var foot = q('[data-m-foot]');
      foot.innerHTML = (m.version ? L.version + ' ' + esc(m.version) + ' · ' : '') + '<button type="button" class="pf-copy">' + L.matchCopy + '</button>';
      foot.querySelector('.pf-copy').addEventListener('click', function (e) {
        var b = e.currentTarget;
        (navigator.clipboard ? navigator.clipboard.writeText(location.href) : Promise.reject()).then(function () {
          b.textContent = L.linkCopied; setTimeout(function () { b.textContent = L.matchCopy; }, 1600);
        }, function () {});
      });
      q('[data-m-body]').hidden = false;
    }, function () { missing(L.unknownMatch); });
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
      if (e.key === 'Tab') {  /* keep focus inside the viewer while it is open */
        var f = $all('button', lb).filter(function (b) { return !b.hidden && b.offsetParent; }), i = f.indexOf(document.activeElement);
        if (f.length) { e.preventDefault(); f[(i + (e.shiftKey ? -1 : 1) + f.length) % f.length].focus(); }
      }
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
      var fmt = function (n) { return Number(n).toLocaleString({ nl: 'nl-BE', de: 'de-DE', fr: 'fr-FR', pl: 'pl-PL' }[lang] || 'en-GB'); };
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
    var T = L.search ? L.search : lang === 'nl'
      ? { ph: 'Zoek maps, wapens, gidsen en posts', none: 'Niets gevonden voor', hint: '↑ ↓ kiezen · Enter openen · Esc sluiten', label: 'Zoeken op de site', quick: 'Snel naar', fail: 'Zoeken is nu niet beschikbaar.' }
      : { ph: 'Search maps, weapons, guides and posts', none: 'Nothing found for', hint: '↑ ↓ to move · Enter to open · Esc to close', label: 'Search the site', quick: 'Jump to', fail: 'Search is unavailable right now.' };
    var script = document.querySelector('script[src*="js/site.js"]');
    if (!script || !window.HTMLDialogElement) { $all('[data-search-open]').forEach(function (b) { b.hidden = true; }); return; }
    var jsBase = new URL('.', script.src), root = new URL(lang === 'en' ? '../' : '../' + lang + '/', jsBase);
    var QUICK = ['download', 'servers', 'guide', 'maps', 'weapons', 'faq'];
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
      fetch(new URL('search-' + lang + '.json', jsBase), { credentials: 'omit' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (d) {
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
    var label = L.top || (lang === 'nl' ? 'Terug naar boven' : 'Back to top');
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
    rail.className = 'rail'; rail.setAttribute('aria-label', L.onPage || (lang === 'nl' ? 'Op deze pagina' : 'On this page'));
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
    var heroSlides = hero && hero.querySelector('.slides'), heroWrap = hero && hero.querySelector('.wrap');
    if (hero) {
      if (tape) {
        var marks = ['N', '15', '30', 'NE', '60', '75', 'E', '105', '120', 'SE', '150', '165', 'S', '195', '210', 'SW', '240', '255', 'W', '285', '300', 'NW', '330', '345'], html = '';
        for (var r = 0; r < 3; r++) marks.forEach(function (m) { html += '<span' + (/^[NESW]+$/.test(m) ? ' class="c"' : '') + '>' + m + '</span>'; });
        tape.innerHTML = html;
      }
      var tx = 0, ty = 0, cx = 0, cy = 0, heading = 0, seen = true, raf = 0, last = 0, lastPx = '', lastPy = '', LOOP = 24 * 60;
      function frame(now) {
        raf = 0;
        var dt = Math.min(50, now - (last || now)); last = now;
        cx += (tx - cx) * 0.06; cy += (ty - cy) * 0.06;
        heading = (heading + dt * 0.006 + cx * dt * 0.05 + LOOP) % LOOP;   /* a slow turn, faster when the cursor leans */
        /* written only when the value moves, so a resting cursor costs no style work */
        var px = cx.toFixed(3), py = cy.toFixed(3);
        if (px !== lastPx || py !== lastPy) {
          lastPx = px; lastPy = py;
          if (heroSlides) heroSlides.style.transform = 'translate3d(' + (cx * -16).toFixed(2) + 'px,' + (cy * -12).toFixed(2) + 'px,0)';
          if (heroWrap) heroWrap.style.transform = 'translate3d(' + (cx * 6).toFixed(2) + 'px,' + (cy * 4).toFixed(2) + 'px,0)';
        }
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
    /* added once the display font is in, so the lettering never jumps when the font swaps */
    if (window.innerWidth > 1100) (document.fonts && document.fonts.load ? document.fonts.load('800 1em "Saira Condensed"').catch(function () {}) : Promise.resolve()).then(function () {
    $all('.band .section-head, .page-head .wrap').forEach(function (head) {
      if (head.closest('.post-head, .studio-hero, #maps')) return;
      var eb = head.querySelector('.eyebrow'); if (!eb) return;
      var word = eb.textContent.trim(); if (!word || /^\d+$/.test(word)) return;
      if (word.length > 13) word = word.split(/\s+/).sort(function (a, b) { return b.length - a.length; })[0];
      var g = document.createElement('span');
      g.className = 'ghost'; g.setAttribute('aria-hidden', 'true'); g.textContent = word;
      head.appendChild(g);
    });
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

  /* cookie-free insights: one page view per page load and one event per download click (tools/server-bridge/tcp_insights.py).
     Nothing is stored in the browser. Campaign tags (utm_*) are read once and then removed from the address bar,
     so a copied link does not carry them on. Global Privacy Control and Do Not Track switch it off entirely. */
  (function () {
    var host = location.hostname;
    if (!TCP_API || !/(^|\.)truecombat\.eu$/.test(host)) return;
    if (navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' || window.doNotTrack === '1') return;
    var base = TCP_API.replace(/\/$/, '') + '/insights/';
    function send(path, obj) {
      try { fetch(base + path, { method: 'POST', body: JSON.stringify(obj), headers: { 'Content-Type': 'text/plain' }, keepalive: true, credentials: 'omit' }).catch(function () {}); } catch (e) { /* never break the page */ }
    }
    var q = {}, keep = [];
    location.search.replace(/^\?/, '').split('&').forEach(function (kv) {
      if (!kv) return;
      var i = kv.indexOf('='), k = decodeURIComponent(i < 0 ? kv : kv.slice(0, i)), v = i < 0 ? '' : kv.slice(i + 1);
      if (/^utm_(source|medium|campaign|content)$/.test(k)) { try { q[k] = decodeURIComponent(v.replace(/\+/g, ' ')); } catch (e) { q[k] = ''; } }
      else keep.push(kv);
    });
    // only the name of the referring site and a screen size class leave the browser
    var ref = ''; try { ref = document.referrer ? new URL(document.referrer).hostname : ''; } catch (e) { ref = ''; }
    var sw = window.screen ? screen.width : 0;
    var hit = { p: location.pathname, r: ref, l: lang, d: !sw ? '' : sw < 700 ? 'phone' : sw < 1100 ? 'tablet' : 'desktop' };
    if (q.utm_source) { hit.s = q.utm_source; hit.m = q.utm_medium || ''; hit.c = q.utm_campaign || ''; hit.t = q.utm_content || ''; }
    send('hit', hit);
    if (Object.keys(q).length && window.history && history.replaceState) {
      try { history.replaceState(history.state, '', location.pathname + (keep.length ? '?' + keep.join('&') : '') + location.hash); } catch (e) { /* ignore */ }
    }
    document.addEventListener('click', function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
      if (!a) return;
      var href = a.getAttribute('href') || '';
      if (!a.hasAttribute('data-download') && !/\/releases\/download\//.test(href)) return;
      var kind = /\.exe(\?|$)/i.test(href) ? 'installer' : /\.zip(\?|$)/i.test(href) ? 'zip' : 'other';
      send('event', { e: 'download', k: kind, p: location.pathname });
    }, true);
  })();

  /* regions that scroll sideways on small screens (tables, the screenshot strip) must be reachable with the keyboard */
  (function () {
    var pending = false;
    function mark() { pending = false; $all('.table-scroll:not([tabindex]), .trio:not([tabindex])').forEach(function (el) { el.tabIndex = 0; }); }
    mark();
    if ('MutationObserver' in window) new MutationObserver(function () { if (!pending) { pending = true; requestAnimationFrame(mark); } }).observe(document.body, { childList: true, subtree: true });
  })();
})();
