# Web bridge for the server list and leaderboards

The website is static, and browsers can't send UDP. `tcp_bridge.py` asks the
master server and the game servers over UDP every minute and serves JSON over HTTP
for the [Servers](../../docs/servers.html) and [Leaderboards](../../docs/leaderboards.html) pages.

It uses only the Python 3.8+ standard library.

```
python tcp_bridge.py --master 127.0.0.1:27950 --listen 127.0.0.1:8090 --stats-dir /srv/tcp/matches
python test_bridge.py      # loopback test with a fake master and game servers
```

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

## Match reports (`tcp-match/1`)

A game server that opts in writes one JSON file per finished match into `--stats-dir`.
Practice matches (`"practice": true`) are ignored. `guid` is hashed by the bridge and never published.

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

## `GET /leaderboard.json?period=all|30d` (`tcp-leaderboard/1`)

Totals per player over the period, for players with at least `--min-matches` (default 3) matches.

```json
{
  "schema": "tcp-leaderboard/1", "updated": "…", "period": "all", "minMatches": 3, "matches": 42,
  "players": [{ "id": "65e7c3ad39e2078b", "name": "Gianni", "matches": 12, "kills": 140, "deaths": 61,
                "headshots": 52, "wins": 48, "timePlayed": 15600, "topWeapon": "M4" }]
}
```
