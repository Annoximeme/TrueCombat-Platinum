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

## Going live

1. Run it on the same machine as `platinum-master`, or any machine that can reach it.
2. Put it behind HTTPS (Caddy, nginx or a Cloudflare Tunnel), for example at `https://api.truecombat.eu`.
3. Set `TCP_API = 'https://api.truecombat.eu'` at the top of `docs/js/site.js` and run `python tools/website/build.py`.

Until `TCP_API` is set, both pages show "Master server offline".

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
    "mode": "Team elimination", "players": 2, "maxPlayers": 16, "password": false,
    "version": "0.30.0", "playerList": [{ "name": "Gianni", "score": 12, "ping": 30 }]
  }]
}
```

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

### `GET /player.json?id=<player id>` (`tcp-player/1`)

Totals, rank with XP progress, rating and peak rating, leaderboard position, per-weapon kills, headshots and
accuracy, and the last 20 matches with their rating change. Also `GET /search.json?q=<name>`,
`GET /recent.json` and `GET /ranks.json`.

### `POST /api/v1/match`

Headers `X-TCP-Server`, `X-TCP-Time` (unix seconds) and `X-TCP-Signature`; body is the report. Answers
200 stored, 409 already stored, 401 bad server/signature/time, 422 refused report, 429 rate limited.

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

## `GET /leaderboard.json?period=all|30d&sort=rating|xp|kills|kd|headshots|wins&mode=&limit=` (`tcp-leaderboard/1`)

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
