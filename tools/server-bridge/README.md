# Web bridge for the server list and leaderboards

The website is static, and browsers can't send UDP. `tcp_bridge.py` asks the
master server and the game servers over UDP every minute and serves JSON over HTTP
for the [Servers](../../docs/servers.html) and [Leaderboards](../../docs/leaderboards.html) pages.

It uses only the Python 3.8+ standard library.

```
python tcp_bridge.py --master 127.0.0.1:27950 --listen 127.0.0.1:8090 --stats-db /srv/tcp/stats.db
python test_bridge.py      # loopback test with a fake master and game servers
python test_stats.py       # loopback test of signed uploads, ranks, ratings, profiles and the upload agent
```

Player stats and ranks live in `tcp_stats.py` (SQLite). The bridge serves them when started with
`--stats-db`; `tcp_stats.py serve` runs the same service on its own if you want it on a different host.

## Hosting

The live instance runs on the project VPS next to `platinum-master`, behind Caddy
at `https://api.truecombat.eu`. `TCP_API` at the top of `docs/js/site.js` points
the site at it; after changing it, run `python tools/website/build.py`. If
`TCP_API` is empty, both pages show "Master server offline".

`--cors` limits which sites may read the JSON. It defaults to truecombat.eu.
Game servers can set the serverinfo cvar `tcp_mode` (for example `Team elimination`) so the list shows a readable
mode. Otherwise pass `--modes "2=Elimination,3=Team elimination"`.

## `GET /servers.json` (`tcp-servers/1`)

```json
{
  "schema": "tcp-servers/1",
  "updated": "2026-11-06T15:35:19Z",
  "master": { "online": true, "listed": 3 },
  "servers": [{
    "address": "203.0.113.5:27971", "name": "Red Server", "map": "obj_railhouse",
    "mode": "Team elimination", "players": 2, "bots": 6, "maxPlayers": 16, "password": false,
    "ranked": true, "eac": 2, "version": "0.30.0", "playerList": [{ "name": "Gianni", "score": 12, "ping": 30 }]
  }]
}
```

`players` and `playerList` count people only. Engine bots answer status queries with ping 0 and are
counted in `bots` instead. `ranked` comes from the server's `tcp_ranked` serverinfo cvar (`sets tcp_ranked 1`
on a server that reports to the leaderboards, `sets tcp_ranked 0` on one that does not); it is `null`
when a server does not set it.
`eac` is the server's Easy Anti-Cheat setting from its `sv_eac` serverinfo key: 0 off, 1 on, 2 required
to join. It is 0 for servers that do not report it. The website shows an anti-cheat badge for 1 and 2.

## Player stats and ranks

No accounts. The game client creates a random `etkey` file in its profile the first time it starts, and its
`cl_guid` is derived from that key. The server reports the guid; the service turns it into a 16-character
one-way player id at once and never stores or publishes the guid itself. Players keep their rank by keeping
their `etkey` file.

**Ranked servers.** Only servers you register can submit matches:

```
python tcp_stats.py --db /srv/tcp/stats.db add-server "Red Server"     # prints the server id and secret key once
python tcp_stats.py --db /srv/tcp/stats.db list-servers
python tcp_stats.py --db /srv/tcp/stats.db disable-server <id>          # stop accepting a server
```

The server operator runs the upload agent next to the game server. It signs every report with the key
(HMAC-SHA256 over `timestamp + "
" + body`, 5 minute clock window), posts it, and sorts the files into
`sent/` and `rejected/`:

```
python tcp_stats_agent.py --dir "<fs_homepath>/tcetest/stats" --url https://api.truecombat.eu     --server <id> --key-file stats-key.txt
```

A game server on the same machine as the service can skip the agent: `--stats-dir` imports its folder directly.

**Game server cvars** (qagame): `g_statsReport 1` writes a report at every map end (0 = never),
`g_statsMinTime 120` seconds a match must last, `g_statsMinPlayers 2` human players needed. Practice
mode, bots and players without a valid guid are never reported.

**What the service refuses:** unknown, disabled or wrongly signed servers, more than 120 uploads per hour
per server, practice matches, matches with cheats enabled (`--allow-cheats` for testing only), matches
shorter than 60 seconds or longer than 6 hours, bad guids, and the same match twice. Values are clamped to
what a match of that length allows.

**Ranks.** XP per match: 10 per kill, 5 per headshot kill, 20 per round won, 30 per objective (flag capture,
bomb plant or defuse), 100 for a match win (25 otherwise), 2 per minute played, minus 25 per team kill.
21 ranks from Recruit (0 XP) to General (105,000 XP); rank *n* needs 250·n·(n+1) XP.

**Skill rating.** Elo, starting at 1000. Team modes compare the two teams' average ratings; free-for-all
compares every pair of players by round wins, kills and suicides. K is 40 for a player's first 10 rated
matches and 24 after that, scaled by the share of the match they played. Players who were present for less
than 60 seconds (or 30% of a short match) are not rated. `recompute` rebuilds every total and rating from the
stored reports, for example after changing these rules.

**Team balance.** Game servers with `g_balanceSkill 1` read `ratings.txt` from their home folder
(`home/tcetest/ratings.txt`) at each map start to even out teams by skill. `serve --ratings-file <path>`
(repeatable, one per server) rewrites it every minute; `export-ratings <path>` does it once. Players without a
rated match are left out and count as 1000.

### `GET /player.json?id=<player id>` (`tcp-player/1`)

Totals, rank with XP progress, rating and peak rating, leaderboard position, per-weapon kills, headshots and
accuracy, and the last 20 matches with their rating change. Also `GET /search.json?q=<name>`,
`GET /recent.json` and `GET /ranks.json`.

### `GET /match.json?id=<match id>` (`tcp-match-page/1`)

One finished match for its page on the website (`match.html?id=`): map, mode, length, rounds, winner, the score per team, the MVP and every player's line (kills, deaths, headshots, damage, objectives, top weapon, XP, rating change). The id is the `id` field of an entry in `/recent.json` or in a profile's `recent` list. It is a hash, so it gives away neither the server id nor the server's own match id.

### `POST /api/v1/match`

Headers `X-TCP-Server`, `X-TCP-Time` (unix seconds) and `X-TCP-Signature`; body is the report. Answers
200 stored, 409 already stored, 401 bad server/signature/time, 422 refused report, 429 rate limited.

## Detailed stats (`tcp-match/2`, game 0.35.0)

Game servers from 0.35.0 write `tcp-match/2`. It is `tcp-match/1` plus the integrity record and an event log,
and every number in it is between real players only: kills, deaths, hits, damage and assists count when both
sides are human, and only while a round is live (no warm-up, waiting, countdown or competitive hold).

Extra fields: `eac` (`start`, `end`, `min`: the server's `sv_eac` at match start, at the end and the lowest value
seen, checked every second), `password` (a join password was set at any point), `ranked` (`tcp_ranked`),
`botSeconds`, `maxBots`; per player `idle` (seconds alive with no input for over 60 s, not counted in
`timePlayed`), `hits` `{head, body, legs}`, `ip` (a hash of the address with a per-match secret salt the server
never writes down, so it only says "same connection" within one match), per weapon `time` and `longest`;
`kills` `[t ms, round, killer, victim, weapon, flags, distance in units, [assists]]` with indices into `players`
(flags: 1 headshot, 2 aimed, 4 crouched, 8 prone, 16 leaning, 32 airborne) and `events`
(`["o", t, round, player, "capture"|"plant"|"defuse"|"return"]`, `["r", t, round, winner, clutch player or -1,
enemies alive, human enemies alive]`).

**Integrity rules** (`integrity()` and `derive()` in `tcp_stats.py`). A match counts only when:

1. it is signed with an issued server key (or imported from a trusted local folder);
2. Easy Anti-Cheat was on for the whole match (`eac.start`, `eac.end` and `eac.min` all at least 1);
3. no join password was set and cheats were off (practice matches are refused as before);
4. at least two real players took part, on both teams in team modes, each present for 2 minutes (or half of a
   short match); two clients behind one address count as one person.

Inside a counted match, same-address opponents never count against each other, only 10 kills on one opponent
count, team kills are kept apart, and accuracy only comes from matches without bots (hit locations and headshot
rate count real hits everywhere). The skill rating only moves on `ranked` matches; unranked matches earn XP and
every other stat. `serve --require-anticheat` (bridge: `--require-anticheat`) refuses everything else, including
`tcp-match/1`; without it the service also takes `tcp-match/1` and uncounted test reports, for development and
for the switch-over while 0.34 servers still report.

**Review.** Numbers no fair player reaches (90%+ accuracy over 50+ shots, 85%+ headshot kills over 20+ kills,
over 4 kills a minute, a kill beyond 400 m) and two players who meet alone 5+ times in 14 days are listed by
`tcp_stats.py review`. `void match <match id>` or `void player <player id>` removes them and rebuilds every
total; `unvoid` restores.

**Routes.**

- `GET /stats.json?id=<player>&scope=all|ranked&period=all|7d|30d|90d|365d` (`tcp-player-stats/1`): every stat
  summed (best value for streaks, longest kill, best clutch) with ratios (`kd`, `headshotRate`, `accuracy`,
  `headHitRate`, `adr`, `winRate`, `kpm`, `avgKillDistance`), weapons, maps, modes, nemesis, favourite victim,
  activity per day for a year and the last 100 ranked ratings.
- `GET /statboard.json?stat=<stat>&scope=&period=&map=&mode=&weapon=&limit=` (`tcp-statboard/1`): a leaderboard
  for any stat or ratio. Ratios need a fair sample (for example 25 kills for K/D, 500 shots for accuracy); the
  answer's `minimum` says which.
- `GET /h2h.json?a=<player>&b=<player>&scope=` (`tcp-h2h/1`): kills on each other, wins as opponents, matches
  together and the last 10 shared matches.
- `GET /statmeta.json` (`tcp-statmeta/1`): the stats, ratios, maps, modes and weapons the boards can filter on.
- `/leaderboard.json` takes `scope=ranked`; sorting by rating or rating gain always uses ranked matches only.

**Several local servers.** The bridge's `--stats-dir` is repeatable and takes `name=folder`, so each server on
the VPS keeps its own id: `--stats-dir /var/lib/tcpgame/home/tcetest/stats --stats-dir
official2=/var/lib/tcpgame/home-unranked/tcetest/stats`.

## Match reports (`tcp-match/1`)

A game server that opts in writes one JSON file per finished match into `--stats-dir`.
Practice matches (`"practice": true`) are ignored. `guid` is hashed by the service and never published.
The native qagame writes this format itself (fields below plus `id`, `cheats`, `duration`, `teamRounds`, and per player
`suicides`, `damageTaken`, `teamDamage`, `objectives`, `won`, `connected` and per-weapon `headshots`).

```json
{
  "schema": "tcp-match/1",
  "server": "Red Server", "address": "203.0.113.5:27971",
  "map": "obj_northport", "mode": "Team elimination", "practice": false,
  "started": "2026-11-06T20:00:00Z", "ended": "2026-11-06T20:21:40Z",
  "rounds": 9, "winner": "specops",
  "players": [{
    "guid": "client GUID or another stable id", "name": "Gianni", "team": "specops",
    "kills": 14, "deaths": 6, "teamKills": 0, "headshots": 5, "damage": 1820,
    "roundsWon": 6, "timePlayed": 1300,
    "weapons": { "M4": { "kills": 12, "shots": 410, "hits": 96 }, "Knife": { "kills": 2 } }
  }]
}
```

`kills` counts enemy kills only, and team kills go in `teamKills`. `timePlayed` is in seconds.

## `GET /recap.json?days=7` (`tcp-recap/1`)

Totals for the last 1 to 92 days (matches, time played, players, new players, kills, headshots), the three
busiest maps, and the standout players: `mostKills`, `mostWins`, `mostXp`, `mostObjectives`, `biggestClimb`
(rating gained), `bestKd` (3 matches or more) and `mostActive`.

## `GET /leaderboard.json?period=all|30d|7d&sort=rating|xp|kills|kd|headshots|wins|season|gain&mode=&limit=&since=&until=` (`tcp-leaderboard/1`)

`since` and `until` (ISO times) select any window, for example a season; `sort=season` ranks by XP earned inside
the window (`periodXp`) and `sort=gain` by rating won inside it (`ratingGain`).

Totals per player over the period, for players with at least `--min-matches` (default 3) matches. Each
player also has `rating`, `kd`, `objectives`, `position` and `rank` (`level`, `title`, `short`, `xp`, `xpThis`,
`xpNext`). `wins` counts matches won.

```json
{
  "schema": "tcp-leaderboard/1", "updated": "…", "period": "all", "minMatches": 3, "matches": 42,
  "players": [{ "id": "65e7c3ad39e2078b", "name": "Gianni", "matches": 12, "kills": 140, "deaths": 61,
                "headshots": 52, "wins": 48, "timePlayed": 15600, "topWeapon": "M4" }]
}
```

## Donation ledger (tcp_kofi.py)

Feeds the live monthly report on `support.html#where`. Ko-fi calls
`POST /kofi/webhook` for every donation and membership payment; the service
checks Ko-fi's verification token, stores the payment in SQLite and serves
`GET /funding.json` (schema `tcp-funding/1`: goal, and per month the amount
received per currency, the count and the supporters list). E-mail addresses,
Ko-fi URLs and messages are never stored, and a name is only shown when the
supporter made their contribution public. Shop orders and commissions are
ignored. Ko-fi retries are de-duplicated on the transaction id.

Install on the VPS: `deploy/install-kofi.sh` (systemd unit `tcp-kofi`, port
127.0.0.1:8091, token in `/etc/tcp-kofi/token`), add the two Caddy routes it
prints, then set the webhook URL in Ko-fi to
`https://api.truecombat.eu/kofi/webhook`.

Payments from before the webhook existed: `tcp_kofi.py --db /var/lib/tcp-kofi/kofi.db add 2026-11-09 5.00 "Name"`
(leave the name out for Anonymous, add `--monthly` for a membership).

Money going out stays manual: add `{"month": "2026-11", "spent": 150}` style
entries to `tools/website/funding.json` (with `received` for the static
fallback) and rebuild the site.

Tests: `python -m unittest test_kofi`.

## Devlog reads and ratings (tcp_devlog.py)

Counts how many people read each devlog post and collects 1 to 5 star
ratings, without visitor tracking: no cookies, no IP addresses, no user
agents are stored. A reader is counted once per post per day through a keyed
hash whose secret only lives for the current UTC day; at midnight the secret
and all hashes are wiped. Post pages only send a read after the post has been
open for about ten seconds, so bounces and crawlers don't count.

- `POST /devlog/read`, `POST /devlog/rate`: called by `docs/js/site.js` on post pages.
- `GET /devlog/public.json` (schema `tcp-devlog/1`): rating averages once a post
  has 5 ratings; read counts only when the service runs with `--public-reads`.
- `GET /devlog/stats.json`: everything, for `truecombat.eu/devlog-stats.html`
  (header `Authorization: Bearer <studio key>`).

Install on the VPS: `deploy/install-devlog.sh` (systemd unit `tcp-devlog`, port
127.0.0.1:8092, studio key in `/etc/tcp-devlog/key`, printed once on the first
run), then add the `/devlog/*` Caddy route it prints. To make read counts
public later, add `--public-reads` to `ExecStart` in
`/etc/systemd/system/tcp-devlog.service` and restart the service; the site
picks them up by itself.

Tests: `python -m unittest test_devlog`.
