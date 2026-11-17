# Staff portal

A private web console for the people who run the official and pickup servers, served at
`https://staff.truecombat.eu` from the VPS. Python standard library only, no build step.

| Area | What staff can do |
| --- | --- |
| Home | One screen on sign-in: players online with a 24-hour sparkline, open and claimed reports, alerts, suspicion, watched players online, bans, appeals, what is scheduled, services and the database snapshot (admins), and the team's latest actions |
| Search and shortcuts | Ctrl+K (or `/`) searches players online and offline, bans by number or appeal code, reports and staff, and runs commands such as `warn Name`, `ban Name` or `announce`; `g` then a key jumps to a page, `?` lists the keys. The menu is grouped and folds away; on a phone it slides in |
| Live updates | Pages update the moment something happens (alerts, reports, chat, staff actions, cases) over one server-sent event stream; the green dot by your name shows it is on, and pages fall back to their timers without it |
| Cases | One place per problem: link reports, bans, appeals and staff actions, add notes and evidence, take it, close it with an outcome; open one from a report or a player page |
| Player timeline | Every play session (server, length, chat lines), name change, report, flag, alert, warning, mute, kick, ban, note, case and piece of evidence about a player in one list, with filters |
| Evidence locker | Screenshots (JPEG, PNG, WebP checked by content), the server demo of a report, chat excerpts that outlive the 30-day chat history, links and statements, kept with a case or a player for a year (open cases: until closed); admins remove evidence |
| Phone app and alerts | Install the portal on a phone or desktop (Add to Home Screen); turn on alerts per device under your name. Urgent alerts always arrive, everything else while you are on duty. Pushes carry no content: the device fetches the alert from the portal with your own sign-in |
| On duty | Go on duty for 1 to 8 hours from the bottom left; the home page shows who is on duty |
| Player history | Players online over 24 hours to 90 days, uptime per server, busiest hours in Belgian time, maps by average players |
| Trial role and rights | Trial moderators watch, warn, look up and write cases; per-person extras or removals on top of any role (presets: event host, appeals reviewer, anti-cheat reviewer, read only). Only the owner hands out admin tools, which still need two-step sign-in |
| Moderator quality | Per staff member: actions, reports closed, median time to take and close a report, bans overturned on appeal or lifted by others, undos, appeals answered (admins) |
| Anti-cheat queue | Anti-cheat detections, suspicion scores of 60 and up and ban dodgers in one list, strongest first; clear, mark as acted on or open a case (admins) |
| Discord /staff commands | Our Discord bot runs summary, reports, take, close, lookup, warn, mute, kick, ban (up to a day) and duty through the portal, as the member who typed them with their own rights; loopback only with a shared token (`install.sh bot-link`). Admin tools stay in the portal |
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
| Punishment ladder | One Punish button per player: the portal picks the next step for the offence (warn, mute, kick, timed ban, permanent) from the player's history in the last 90 days |
| Undo | Bans and mutes can be undone for five minutes from the toast or the ban list (a kick or a team move has nothing to undo) |
| Ban appeals | Every ban message carries a six-character code; players appeal at `/appeal` (no sign-in), an admin who did not make the ban accepts or denies it from Reports, the player checks the answer with the same code |
| Alerts | Server down and back, reports piling up, suspicion scores, watchlist joins, possible ban dodgers, chat filter hits, moderator bans; in the portal and in a staff Discord channel through a webhook |
| Suspicion score | 0-100 per player from anti-cheat detections, reports, automatic flags, accuracy, K/D, headshot rate and links to banned players; 60 and up raises an alert |
| Stats review | Players whose stats stand out, with match history, one click to mark them checked |
| Ban-dodger hints | A new identity on the anti-cheat account (strong) or address (weak) of a banned player |
| Chat filter | Words with `*` wildcards or regular expressions; flag, warn, mute or kick, at most once a minute per player |
| Team-kill and AFK watch | Two team kills in a match warn, three flag; idle players are flagged at 2 minutes and moved to spectators at 5 |
| Watchlist | Watch a player with a reason; staff are alerted when they join any server |
| Saved replies | Reasons and warnings staff reuse, picked from every dialog |
| Linked Discord | The Discord account a player linked through the bot, shown on the player page; search by Discord id |
| Demos | A report opens the server demo at the reported moment (needs `sv_autoDemo 1`) |
| Schedule | Announcements, map changes and restarts at a set time, once or repeating |
| Event mode | One switch for a private match: random password, no bots, no balance, no votes; switches back afterwards |
| Live map | Top-down layout with every player's position, refreshed every two seconds; admins only, audited, and closed to anyone whose linked account is playing on that server |
| Settings | Whitelisted server settings with labels, a full history and one-click rollback; "Keep" re-applies a value after restarts |
| Two-step sign-in | Authenticator-app codes, set up by scanning a QR code drawn by the portal itself; required for admin and owner rights |
| Weekly report | Monday 08:00 Belgian time: bans, reports, appeals, peaks and busiest staff, in the portal and the staff channel |

## Roles

| | Moderator | Admin | Owner |
| --- | :-: | :-: | :-: |
| View servers, chat, reports, lookup, health | ✓ | ✓ | ✓ |
| Warn, mute, move, kick, reply in chat, announce | ✓ | ✓ | ✓ |
| Ban up to 24 hours | ✓ | ✓ | ✓ |
| Longer and permanent bans, lift bans | | ✓ | ✓ |
| Change map, rotation, restart match, restart a server | | ✓ | ✓ |
| IP addresses, audit log, staff list | | ✓ | ✓ |
| Punish, watchlist, saved replies, schedule announcements | ✓ | ✓ | ✓ |
| Answer appeals, chat filter, event mode, settings, live map, stats review | | ✓ | ✓ |
| Make or change admins, reset someone's two-step sign-in | | | ✓ |

Owners come only from `owners` in the config: taking someone out of that list ends their owner rights at the next start.

Admin and owner rights need two-step sign-in (`"require_2fa": true`, the default). Without it those accounts
sign in as moderators until they set it up under their name in the menu. A lost phone:
`python3 tcp_staff_portal.py --config /etc/tcp-staff-portal/config.json --reset-2fa DISCORD_ID`.

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
* Stats review and suspicion use the stats service's private `/staff/` routes (loopback only, `X-Staff-Token`).
  `install.sh stats-link` creates the token and hands it to both services as a systemd credential.
* Linked Discord accounts are read from the Discord bot's database, read-only.
* The Insights page (admins) reads `/insights/stats.json` from the website insights service on 127.0.0.1:8094
  (`tools/server-bridge/tcp_insights.py`). `install.sh insights-link` copies that service's studio key into the
  portal's `insights-key` credential; an empty file leaves the page saying it is not connected.
* Alerts go to the webhook in `/etc/tcp-staff-portal/staff-webhook` (empty file: portal only). Set
  `alerts.ping_role_id` to ping a role on urgent ones and `alerts.kinds` to pick which kinds reach Discord.
* Server demos are read from `<home>/tcetest/svdemos` (`demo_timezone` is the server's clock for the file names).
* Restarting a game server goes through a polkit rule that allows `restart` on exactly the four game units.

## Bug reports

From 0.36.0, F12 in game sends the report straight to `POST https://staff.truecombat.eu/api/bugreport`
(the game's `cl_bugReportEndpoint`) as one JSON body, `"format": "tcp-bugreport/1"`:

| Field | |
|---|---|
| `category` | `Bug`, `Suggestion` or `Feature` |
| `text` | what the player wrote (16 KB kept) |
| `map`, `pos` [x, y, z], `server` (ip:port, empty offline), `match` | where it happened |
| `build`, `renderer`, `ping`, `fps`, `time`, `hw` {…} | the player's setup |
| `console` | the last ~200 console lines (64 KB kept) |
| `name`, `guid`, `puid` | who sent it; `guid` is turned into the player id and not stored |
| `screenshot_jpg` | base64 JPEG, at most 1 MB; anything that isn't a JPEG is dropped |

The body may be up to 1.6 MB. Answers: `201 {"ok": true, "id": …}`, `400` bad body, `413` too big, `429` over
6 an hour per address, `503` inbox full. The game keeps a local copy whenever the answer isn't 2xx.

Reports land under Reports › Bug reports with the screenshot, the context, and a button for the console
and hardware; a short alert goes to the staff Discord (kind `bugreport`) linking to the inbox, without the
screenshot. Screenshots live in `<data_dir>/bugshots` and go with their report when closed reports are
pruned, and stop being kept once they fill `bugshot_max_mb` (500). Player text in the Discord alert is
escaped, so it can't carry links or mentions. Plain-text posts with `X-Report-Category` still work for older tools.

## Staff badge keys

Every staff member gets their own in-game staff key under their name (bottom left) › Staff badge in game.
The browser makes the Ed25519 key pair and downloads `staff.key` (`TCPSTAFF1 <id> <seed>`). Only the
public half reaches the portal. The portal writes the public keys to `<game dir>/staffkeys/staffkeys.txt`
for every server (or `staff_keys_file` per server) and sends `staffkeys_reload` over rcon. Game servers
from 0.36.0 read that list next to the keys built into the game (see `game/STAFF-KEYS-INTEGRATION.md`).

**Install in game** (the default) opens a one-time `truecombat://staffkey/<code>` link (10 minutes, single
use). The launcher (2.1+, see `launcher/STAFF-KEY-INSTALL.md`) makes the key pair itself, claims the link at
`POST /api/staffkey/claim` with the public half and writes `profile\staff.key`, so the secret never leaves
that PC. A claim only works while the person who made the link still has a portal session. Downloading the
file stays available as a fallback. Turn it on with `"launcher_key_install": true` once launcher 2.1 is released;
until then the portal offers the download only.

A key stops working when a newer one is made, when an admin revokes it (Staff page), when the person
loses staff access (revoked in the portal or Discord role removed, seen at their next portal visit), or
after `staff_key_idle_days` (default 60, 0 = never) without signing in to the portal.

### Staff certificates (game 0.38.0+, launcher 2.5+)

So the badge works on every server, community and offline ones included, the portal signs each active key into
a certificate with a root Ed25519 key. Every game server checks it against the root public keys built into the
game (`game_src/native/tcp_staff_roots.h`, two slots for rotation), with no key list and no network call. The key
list above stays as a second path.

- Certificate line, public data (useless without the staff member's private key):
  `TCPSTAFFCERT1 <root id> <key id> <role> <issued> <expires> <public key hex> <name hex> <signature hex>`, signed
  over `TCP-STAFF-CERT-1\n<root id>\n<key id>\n<role>\n<issued>\n<expires>\n<public key hex>\n<name hex>`.
- `GET /api/staffcert?id=<key id>` (no session; 60 per hour per address) returns `{"cert", "expires"}` for an
  active key and 404 for an unknown, revoked or idle key, or while no root is set up. The launcher claim answer
  (`POST /api/staffkey/claim`) carries the first certificate too. Certificates last `staff_cert_days` (30).
- The launcher stores it as `profile\staff.cert` and renews it at most once a day while it has less than 10 days
  left; the game writes the public key id to `profile\staff.keyid` for that. A revoked key stops working when its
  certificate runs out; for faster removal list the key id in `tcp_staff_revoked.h` in the next release.

Root key (once; never in the repo, a release or a project file):

    sudo python3 /opt/tcp/staff-portal/tcp_staff_portal.py --config /etc/tcp-staff-portal/config.json \
        --make-staff-root r1 --root-out /etc/tcp-staff-portal/staff-root     # root:root 0600, never overwritten

It prints only the public key line for `tcp_staff_roots.h` (slot r1). Then uncomment
`LoadCredential=staff-root:...` in the unit, `systemctl daemon-reload`, restart the portal, and ship a game
release with that public key. Rotation: make r2 the same way, ship it next to r1, switch the credential to r2,
then drop r1 in a later release.

## Run and test

```
python3 test_staff_portal.py      # 53 loopback tests with a fake game server and stats service
TCP_STAFF_DEV=1 python3 tcp_staff_portal.py --config my-local.json
```

With `"dev_login": true` in the config **and** `TCP_STAFF_DEV=1` in the environment, `/auth/dev?role=admin`
signs in from 127.0.0.1 without Discord.

Discord role ids for the trial role go in `discord.trial_role_ids`. Never set either on the VPS.

## Deploy (VPS)

1. DNS: `staff` A record to the VPS (and AAAA for IPv6).
2. Discord Developer Portal, the bot's application: OAuth2 redirect `https://staff.truecombat.eu/auth/callback`.
3. `sudo ./deploy/install.sh inspect` (read-only), then put the client secret in
   `/etc/tcp-staff-portal/client-secret`, fill `owners`, `client_id`, `guild_id` and the role ids in
   `/etc/tcp-staff-portal/config.json`.
4. `sudo ./deploy/install.sh install` (rolls back by itself if the portal does not answer), then
   `sudo ./deploy/install.sh caddy`.
5. Optional, each on its own: the staff channel webhook URL into `/etc/tcp-staff-portal/staff-webhook`;
   for the stats review queue, first deploy the updated `tools/server-bridge/tcp_stats.py` and `tcp_bridge.py`
   (they add the `/staff/` routes), then `sudo ./deploy/install.sh stats-link` (restarts the stats service, rolls
   back if it does not answer);
   `sv_autoDemo 1` in each game server's cfg for report demos;
   for the Insights page, install the insights service (`tools/server-bridge/deploy/install-insights.sh`), then
   `sudo ./deploy/install.sh insights-link`.
6. Owner and admins: set up two-step sign-in under your name, bottom left.

Data lives in `/var/lib/tcp-staff-portal/portal.db` (SQLite). It also holds two-step sign-in secrets and the Discord
sign-in tokens of open sessions, so a backup of it belongs in the private backup repository only. Chat is kept 30 days, sightings
player-count samples and play sessions 90 days. Evidence files live in
`/var/lib/tcp-staff-portal/evidence/` (2 GB quota by default, `evidence_quota_mb`).

Every night at 04:20 UTC the portal writes `/var/lib/tcp-staff-portal/backups/portal-snapshot.db`: a checked copy without
sign-in sessions, one-time key links or the undo list (admins can also make one from Health). To send it off-site, add that
path to the `SECRET` list of `/opt/tcp/backup/tcp_offsite_backup.py`, which encrypts it before it leaves the VPS.

`tcp-staff-watch.timer` checks the portal from outside every two minutes as its own unit: two failed checks in a row post
"Staff portal is down" to the staff webhook, the next good one says it is back, and a missing or old snapshot is reported
once a day. Player IP addresses and identity keys in the live server view are sent to admins only.

## Devlog comments (1.5.0)

Moderation for the comments players post under devlog posts on truecombat.eu (accounts service 1.3.0,
`tools/accounts/tcp_comments.py`). Menu: Moderation, Devlog comments (moderators and up; closing a whole post is
admin). The portal reads and acts through the accounts service's loopback `/internal/comments/*` with its own token
(credential `accounts-token`, `install.sh accounts-link`), which reaches comments and nothing else in the accounts
service.

* **Needs a look:** held comments (first comment of an account with no linked PC, word filter, link from an account
  with no linked PC) and reported ones, with account age, matches, linked PC, clean record and who reported it.
* **Actions:** publish (the author posts freely from then on), hide, keep hidden, restore, remove (text kept 90 days
  for appeals), no action (closes the reports), pin one comment per post, reply as team (posted under the staff
  member's own TrueCombat account, which needs to exist), pause a player's comments for 1, 7 or 30 days or for good,
  close or reopen a post (admin).
* **Alerts:** once a minute the portal checks how many comments wait; when the number grows it raises a `comments`
  alert (and the staff Discord post) with counts only, never comment text.
* **Audit log:** every action, as `comment.<action>`, with the author and the first 200 characters.
