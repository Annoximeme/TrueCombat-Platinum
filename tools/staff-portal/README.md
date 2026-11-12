# Staff portal

A private web console for the people who run the official and pickup servers, served at
`https://staff.truecombat.eu` from the VPS. Python standard library only, no build step.

| Area | What staff can do |
| --- | --- |
| Servers | Live view of every server: map, mode, players and bots, ping, score, K/D, anti-cheat state per player |
| Players | Warn (private), mute (text and voice, follows the player across maps and servers), move team or to spectators, kick |
| Bans | Timed or permanent bans that hold on every server at once (identity, anti-cheat account, optional IP); automatic expiry; a sync job puts a ban back on any server that lost it |
| Server control | Announce, change map, skip to the next map, edit the rotation, restart the match |
| Live chat | All chat from every server, team chat marked; reply as staff to one server or all |
| Lookup | Any name a player has used, servers, anti-cheat id, stats and recent matches, full record, chat history, staff notes; IP addresses and shared-address matches for admins |
| Reports | In-game `/report` reports and automatic flags from every server, plus F12 bug reports; take, close with a resolution, reopen |
| Audit log | Every action, sign-in and refused sign-in, with who, when, target and the server's answer |
| Staff | Access follows Discord roles; the list adds people without the role, promotes to admin or locks someone out |
| Health | CPU, memory, disk, every service's state, restarts and problems in the last 24 hours; restart a game server |

## Roles

| | Moderator | Admin | Owner |
| --- | :-: | :-: | :-: |
| View servers, chat, reports, lookup, health | ✓ | ✓ | ✓ |
| Warn, mute, move, kick, reply in chat, announce | ✓ | ✓ | ✓ |
| Ban up to 24 hours | ✓ | ✓ | ✓ |
| Longer and permanent bans, lift bans | | ✓ | ✓ |
| Change map, rotation, restart match, restart a server | | ✓ | ✓ |
| IP addresses, audit log, staff list | | ✓ | ✓ |
| Make or change admins | | | ✓ |

Sign-in is Discord OAuth (`identify guilds.members.read`). The role comes from, highest first: `owners` in the
config, the staff list in the portal (which can also revoke), then the Discord role ids in the config. Rights are
checked against Discord again every 10 minutes, so removing someone's Discord role ends their session.

## Server-side commands

0.35.0 servers already give the portal kick, bans, spectate, map control, chat and anti-cheat state. Warn, mute,
team moves, the staff chat line and the detailed player list need `game/tcp_staff_admin.h`, which ships with the
0.36.0 server (`python game/apply_staff_admin.py <game_src>`). The portal asks each server `tcp_staffcaps` and
switches those buttons on per server; on an older server they explain why they are unavailable.

## How it talks to the servers

* rcon over 127.0.0.1, one command at a time per server. Passwords are copied from each server's cfg into
  root-only files and handed to the service as systemd credentials. They never reach a browser.
* Chat comes from the game's own `TCP_NATIVE_SAY` log lines (journald); names are matched from the live player list.
* Reports are read from `<home>/tcetest/reports` and `reports/sent` (the Discord bot moves posted reports there).
  The portal only reads them.
* Stats and recent matches come from the stats service on 127.0.0.1:8090 (`player.json`, `search.json`).
* Restarting a game server goes through a polkit rule that allows `restart` on exactly the four game units.

## Bug reports

`POST https://staff.truecombat.eu/api/bugreport` takes the plain-text report the game writes on F12
(`X-Report-Category: Bug|Suggestion|Feature`), at most 6 an hour per address and 96 KB each. Set
`cl_bugReportUrl` to that address once the launcher uploads `bugreports/pending.txt`.

## Run and test

```
python3 test_staff_portal.py      # 15 loopback tests with a fake game server and stats service
TCP_STAFF_DEV=1 python3 tcp_staff_portal.py --config my-local.json
```

With `"dev_login": true` in the config **and** `TCP_STAFF_DEV=1` in the environment, `/auth/dev?role=admin`
signs in from 127.0.0.1 without Discord. Never set either on the VPS.

## Deploy (VPS)

1. DNS: `staff` A record to the VPS (and AAAA for IPv6).
2. Discord Developer Portal, the bot's application: OAuth2 redirect `https://staff.truecombat.eu/auth/callback`.
3. `sudo ./deploy/install.sh inspect` (read-only), then put the client secret in
   `/etc/tcp-staff-portal/client-secret`, fill `owners`, `client_id`, `guild_id` and the role ids in
   `/etc/tcp-staff-portal/config.json`.
4. `sudo ./deploy/install.sh install` (rolls back by itself if the portal does not answer), then
   `sudo ./deploy/install.sh caddy`.

Data lives in `/var/lib/tcp-staff-portal/portal.db` (SQLite). Chat is kept 30 days and sightings 90 days.
