# TrueCombat: Platinum Discord bot

Our own Discord bot, running on the VPS next to the stats service, the master
server and the official servers. It reads everything locally on the box
(game servers over UDP, the stats bridge on 127.0.0.1:8090, the website
folder) and only talks to Discord and the public GitHub releases API.

| | |
|---|---|
| **Live server cards** | One card per official server, edited in place every minute: map with picture, mode, players and scores, top of the leaderboard, community servers. Turns red after two missed answers, so a map change never flickers it. **How to join**, **Server list** and **Leaderboards** buttons. Replaces the webhook feed (`tcp-status`). |
| **Feed** | "New #1 on the leaderboard" (confirmed on two checks) and "Match on now" when 4+ people are on an official server, pinging the opt-in **Match alerts** role, at most every 3 hours. |
| **Stats** | `/profile` (rank with XP bar, rating and peak, position, win rate, K/D, headshots, time played, favourite weapons, last five matches with rating change), `/top` (by rating, XP, kills, K/D, headshots or wins; all time or 30 days), `/compare`, `/servers`, `/matches`. Player names autocomplete. |
| **Account linking** | `/link` gives a one-time code; the player enters `/link CODE` in the game console (or `!link CODE` in chat) on an official server and Discord confirms within seconds. Needs the game patch in `game/` (next release). No passwords, no sign-up, the game key file stays the identity. |
| **Releases** | New GitHub releases are staged in the private staff channel with **Publish**, **Add patch notes** and **Skip**. Nothing reaches the community until someone presses Publish. Every patch-notes link in the announcement opens the version's own page on truecombat.eu (for example `truecombat.eu/release-0-37-0`); until the site has built that page, it opens the version's entry on the patch notes page instead. In auto mode the bot waits up to 30 minutes for the page before posting. Patch notes split on `----- NEXT DISCORD MESSAGE -----` exactly like the files we write. |
| **Devlog** | New devlog articles are posted automatically with their cover image. |
| **Roles** | Rank tiers from linked profiles (Enlisted, Non-Commissioned Officer, Officer, General Staff), **Top 10** by skill rating, **Verified player**. Opt-in **Match alerts**, **Playtester** and **Event alerts** via `/notify` or the get-started panel. |
| **Welcome** | New members get a welcome card with install, guide, match and linking steps, plus the alert buttons. |
| **Pickup queue** | Competitive pickup matches for when there aren't enough players for matchmaking. Players press **Join queue** (or `/pickup join`). When two full teams are queued (3v3 by default) everyone gets a 60-second ready check. Anyone who doesn't accept is dropped, and the others stay at the front of the queue. Teams are balanced on skill rating, trying every possible split, and unrated players count as average. The bot then claims a free match server over local rcon, sets a new password, turns on competitive match mode and loads a map, and sends each player a DM with their team and a join link (with a **Join details** button as a fallback). With `g_pugTeams 1` every player lands on the right team automatically, through the launcher's `truecombat://join` link or the console line in the DM. When the server empties it posts the result (rounds, MVP, each linked player's rating change), locks the server with a fresh password and starts the next waiting group. Off until the match servers exist. |
| **Player reports** | Every in-game `/report` (from the online-play game patch) lands in the private staff channel with the reported player's stats for that map, accuracy, the reason, a repeat count and a **Handled** button. When the server records demos, the card names the demo file and the minute and second to jump to. Automatic cheat flags from the server get a red card. Files are moved to `reports/sent/` once posted. |
| **Server admin** | `/admin players`, `kick`, `ban` (30m to permanent; a game-key ban is applied on every official server), `banguid`, `unban`, `banlist`, `map` and `say`, over local rcon. Every action is logged to the staff channel. |
| **Events and playtests** | `/event create` posts a card with Going / Maybe / Can't make it buttons, a live roster, a slot limit with an automatic waitlist, a matching Discord scheduled event, and a reminder ping to everyone going 15 minutes before. Times are entered in Belgian time and shown to everyone in their own. |
| **Match reports** | A card after every finished match with four or more players: the score, both scoreboards with each player's rating change, the player of the match, and any achievements unlocked. |
| **Achievements** | 28 milestones for ranked play (first win, kill and win counts, rating marks, win streaks, standout matches, season champion). Announced in the match report, shown on `/profile`, listed with what to go for next in `/achievements`. Rules live in `tcpbot/achievements.py`. |
| **Weekly recap** | Every Monday evening: matches, players and hours played, the week's top fragger, most wins, best K/D, biggest climber, objective specialist and the most played maps. `/recap` shows it on demand. |
| **Seasons** | A season follows the calendar (a month by default, or a quarter). Season points are the XP earned in ranked matches during the season. `/season` shows the race; when a season ends the final standings are announced and the winner holds the **Season champion** role until the next one. |
| **Personal alerts** | By DM, each with its own cooldown: `/alerts player` when someone you follow joins an official server, `/alerts map` when a map you like comes up with players on it, `/alerts rank` when someone passes you on the leaderboard. |
| **Teams and scrims** | `/team create`, invite by DM button, roster, captain hand-over and a team ladder with its own rating. `/scrim challenge` puts a challenge in front of the other captain; on Accept the bot claims a match server, names both sides and sends every player their join line. The winner is read from the scoreboard and the ladder moves. |
| **Tournaments** | Staff open one with `/tournament create`, captains sign up with a button. `/tournament start` draws a single-elimination bracket seeded on team rating (top seeds get the byes). Captains start their match with `/tournament play`; winners advance on their own and the bracket card updates. |
| **Bug reports** | `/bug` opens a short form. Reports land in a private tracker channel as cards staff move through Confirmed, Fixed, Can't reproduce and so on; the reporter gets a DM on every change. Optionally one click files it as a GitHub issue. |
| **Player accounts (1.3.0)** | Members with a [player account](https://truecombat.eu/account) get their roles from it: one record across every PC they linked, plus **Clean record** and **Trusted player** roles that follow the account's badges. An opt-in **weekly report** by DM every Monday evening (only to players who played that week: matches, kills and K/D against the week before, rating change, best match, new medals). A live **Looking for a squad** board in its own channel. Staff `/account lookup`, `/account ban` (covers every PC the account ever linked, survives deleting the account), `/account unban` and `/account bans`. |
| **Suggestions** | `/suggest` posts an idea to the suggestions channel with 👍 / 👎 buttons (one vote per member). Staff mark it Planned, In progress, Shipped or Not planned, and `/suggestion top` lists the most wanted. |
| **Map votes** | A weekly ballot (or `/mapvote start`) with a button per map and a few votes per member. The result is announced, staff get the winners, and with `map_votes.apply = "rcon"` the rotation is set on the servers directly. |
| **Chat bridge** | Public game chat appears in a Discord channel per server. Team chat and commands (link codes) never leave the server. `/chat` sends a line back into the game: staff only by default, or every linked player. |
| **Raid watch** | Eight joins inside a minute alerts staff with the accounts and their ages, and a button that pauses invites for 30 minutes. `/mod automod` creates Discord AutoMod rules for mention floods, spam and slurs. |
| **Ban appeals** | `/appeal` opens a form; the appeal reaches staff with the player's profile and Accept / Deny buttons, and the answer goes back by DM. One open appeal at a time, 14 days between attempts. |
| **Instant answers** | `/ask` answers common questions (install, requirements, ranks, linking, servers, crashes and more) from answers the team wrote in `tcpbot/faq.py`. No language model, so it never makes things up; anything it can't answer goes to staff with one button. |

Everything the bot says is written in `tcpbot/embeds.py` and the module that owns the feature, so the voice stays consistent.

## Commands

| Everyone | Staff (Manage Server) |
|---|---|
| `/profile [player] [member]` | `/setup roles` · create or adopt the bot's roles |
| `/top [sort] [period] [count]` | `/setup panel` · post the get-started panel in this channel |
| `/compare first [second]` | `/setup check` · channels, permissions and config at a glance |
| `/servers` · `/matches` | `/release announce [version] [notes file]` · stage a release for review |
| `/link` · `/unlink` | `/release notes file [version]` · attach Discord patch notes to a staged release |
| `/notify` · `/events` · `/help` | `/event create` · `/event cancel` (Manage Events) |
| `/pickup join` · `/pickup leave` · `/pickup status` | `/link-admin show` · `/link-admin remove` |
| `/season` · `/recap` · `/achievements [player]` | `/admin players` · `kick` · `ban` · `banguid` · `unban` · `banlist` · `map` · `say` (Kick Members) |
| `/alerts player` · `map` · `rank` · `list` · `remove` | `/pickup end` · `/pickup reset` · `/pickup servers` |
| `/team create` · `invite` · `join` · `leave` · `kick` · `captain` · `disband` · `info` · `list` | `/scrim result` · confirm a scrim the scoreboard couldn't settle |
| `/scrim challenge team [map]` | `/tournament create` · `start` · `result` · `cancel` |
| `/tournament bracket` · `/tournament play` | `/suggestion status` |
| `/bug` · `/suggest` · `/suggestion top` | `/mapvote start` · `/mapvote close` |
| `/ask question` · `/appeal` | `/mod raid` · `/mod automod` |
| `/chat message [server]` (when the bridge allows it) | |

Staff commands are hidden from members by default. Server owners can fine-tune
who sees what under Server Settings → Integrations.

## First-time setup

1. **Discord Developer Portal**, app *TrueCombat: Platinum* (1569008112407683072, the same app Rich Presence uses, so the bot and players' game status share one name and logo):
   * **Bot** → Reset Token, copy it. Turn on **Server Members Intent**.
   * **Installation** → Guild Install with scopes `bot` and `applications.commands` and the permissions
     View Channels, Send Messages, Embed Links, Attach Files, Read Message History,
     Manage Roles, Manage Events, Create Events. Open the install link and add the bot to the server.
     Manage Server is optional: only `/mod raid` (pausing invites) and `/mod automod` need it.
2. **Channels**: copy the ids (Developer Mode → right-click → Copy Channel ID) into `/etc/tcp-discord-bot/config.json`.
   `staff` must be a private channel. `announcements` may be an Announcement channel; the bot then also
   publishes to following servers.
3. **Install on the VPS** (from this folder):

   ```sh
   sudo ./deploy/install.sh                                  # code, venv, service, starter config
   sudoedit /etc/tcp-discord-bot/config.json                 # guild_id and channel ids
   read -rs T && printf '%s' "$T" | sudo ./deploy/install.sh --token-stdin --retire-webhook; unset T
   ```

   `--retire-webhook` stops the old webhook status timers once the bot's own cards take over.
   Delete the old webhook card in #server-status by hand.
4. In Discord: `/setup roles`, drag the bot's role above the roles it created, `/setup panel` in your
   get-started channel, then `/setup check`.

The profile picture is set from `assets/avatar.png` (our logo) on the first start, and again only when the file changes.

## Config

`/etc/tcp-discord-bot/config.json` (root:tcpbot, 0640). Everything has a sensible default except `guild_id`
and the channel ids; see `tcpbot/config.py` for every option. The ones worth knowing:

| Key | Default | |
|---|---|---|
| `servers[]` | Official #1 | One live card per entry: `key`, `name`, `host`, `port`, `public_address`, `match_type`, optional `channel`, `match_alerts` |
| `releases.mode` | `draft` | `draft` waits for Publish in the staff channel; `auto` announces as soon as GitHub publishes |
| `releases.ping_role_id` | 0 | Role to ping with release announcements |
| `match_alerts.min_players` / `cooldown_minutes` | 4 / 180 | When "Match on now" fires |
| `linking.dirs` | Official #1's `links/` | Folders game servers write link requests into |
| `reports.dirs` | Official #1's `reports/` | Folders game servers write `/report` files into; posted to `channels.reports` (default: staff) |
| `roles.rank_tiers` / `top10` / `verified` | on | Which earned roles the bot manages |
| `pickup.enabled` / `channel` / `team_size` | off / none / 3 | The pickup queue and its channel; 3 = 3v3 |
| `pickup.servers[]` | none | Match servers: `key`, `host` (must be 127.0.0.1), `port`, `public_address`, `rcon_credential`, optional `stats_name` (the name its results are stored under) |
| `pickup.stats_server` | "" | Name the match servers report under in the stats service, used to find the result |
| `channels.matches` / `teams` / `bugs` / `suggestions` / `votes` / `support` | 0 | Where match reports, team challenges, the bug tracker, suggestions, map votes and questions for staff go. Each falls back to a sensible channel (`/setup check` lists them); `/suggest` stays off until `suggestions` is set |
| `match_reports.min_players` | 4 | Smaller matches are not reported |
| `recap.weekday` / `hour` | 0 / 18 | When the weekly recap is posted (Monday 18:00) |
| `seasons.length` | month | `month` or `quarter` |
| `alerts.*` | | Cooldowns and the number of alerts a member may hold (10) |
| `teams.max_members` / `challenge_minutes` | 8 / 30 | Roster size, and how long a scrim challenge stays open |
| `feedback.github_repo` | "" | `owner/repo` to enable **File on GitHub** on bug cards; the token is stored with `install.sh --secret-stdin github-token` |
| `map_votes.enabled` / `weekday` / `hour` / `hours_open` | off / 4 / 18 / 48 | The weekly ballot (Friday 18:00, open two days) |
| `map_votes.apply` / `servers` / `rotation_command` | notice / none | `rcon` sets the rotation on the listed servers with the command; `notice` only tells staff |
| `chat_bridge.servers[]` | none | `key` (a server from `servers`), `channel`, and `unit` (systemd service to follow) or `log` (console log file) |
| `chat_bridge.relay_to_game` | staff | Who may use `/chat`: `off`, `staff` or `linked` |
| `moderation.raid_joins` / `raid_seconds` | 8 / 60 | What counts as a join wave |
| `staff_role_ids` | none | Roles that count as staff besides Manage Server |
| `timezone` | Europe/Brussels | How staff-entered event times are read |

The token lives in `/etc/tcp-discord-bot/token` (root, 0600) and reaches the bot as a systemd credential.
It is never in the config, on a command line or in the logs.

## Operations

```sh
journalctl -u tcp-discord-bot -f                      # live log
sudo systemctl restart tcp-discord-bot                # after a config change
sudo -u tcpbot TCPBOT_CONFIG=/etc/tcp-discord-bot/config.json \
     /opt/tcp/discord-bot/venv/bin/python -m tcpbot preview    # render the cards as JSON, no Discord
```

State (links, events, card message ids) is a single SQLite file, `/var/lib/tcp-discord-bot/bot.db`.
Updating is `git pull` (or copying the new kit) and `sudo ./deploy/install.sh` again; config, token and state are kept.
`sudo ./deploy/uninstall.sh` removes the service and code, `--purge` also removes config, token and state.

The service runs as the unprivileged `tcpbot` user with a read-only system, no home folder and write access
only to its state folder and the link and report folders.

## Pickup match servers

The queue needs one or more private match servers on the VPS with competitive match mode in the game
(the next release) and rcon on 127.0.0.1. Copy each server's rcon password from its own config into a
root-only credential that systemd hands to the bot. The password never appears on a command line:

```sh
sudo ./deploy/install.sh --rcon-from-cfg rcon-match1=/path/to/match1-private.cfg
```

The same works for the official servers, so they can use `/admin` (`rcon-official1`, then
`"rcon_credential": "rcon-official1"` on the server entry). Set `pickup.join_url` to
`https://truecombat.eu/join.html` once the release with launcher 1.5.0 is out.

Then add it to `pickup.servers`, set `pickup.channel` and `pickup.enabled`, and restart the bot.
`/pickup servers` shows whether each server answers on both the status port and rcon.
Between matches the bot keeps every match server locked with a random password.

## What needs what

* **Match reports with scoreboards, the weekly recap and seasons** use three additions to the stats service
  (`/recap.json`, and `since` / `until` on the leaderboard; match scoreboards come from the website's `/match.json`) in `tools/server-bridge/tcp_stats.py`.
  Until the VPS runs that version, match reports use the short form and `/season` and `/recap` say they're on the way.
  Nothing breaks.
* **Scrims and tournaments** use the pickup match servers (`pickup.servers`). The pickup queue itself can stay off.
  A result is read from the scoreboard through linked profiles, so teams whose players have used `/link` get
  automatic results; otherwise staff confirm with `/scrim result` or `/tournament result`.
* **The chat bridge** needs read access to each server's console output. With `unit` entries `install.sh` adds the
  bot to the `systemd-journal` group; with `log` entries it grants read access to that one file. Chat lines are
  recognised with `chat_bridge.patterns` (regular expressions with a `text` group and a `name` or `slot` group):
  check them against a real log line when enabling the bridge.
* **Map votes with `apply: "rcon"`** need `rcon_credential` on the server entries, like `/admin`.
* Re-run `/setup roles` once after updating, so the **Season champion** role exists.

## Player accounts (1.3.0)

Reads the account service on the VPS (`tools/accounts/tcp_accounts.py`, 127.0.0.1:8095). Off until the bot has its token:

```sh
sudo cat /etc/tcp-accounts/internal-token | sudo ./deploy/install.sh --secret-stdin accounts-token
```

(use the path where the account service keeps its `internal-token` credential). Then:

1. `/setup roles` once, so **Clean record** and **Trusted player** exist (`roles.badges: false` leaves them out).
2. Set `channels.lfs` to a read-only channel for the *Looking for a squad* board (0 = off).
3. `accounts.weekly` sets the day and hour of the weekly report (default Monday 19:00 Belgian time).

An account outranks a `/link` link for roles: its stats id holds every PC the player linked. If the account service
is down, roles are left as they are. The weekly report needs `week.json` from the stats service (accounts 1.1.0 patch).

## Game side (account linking)

`game/link-command.patch` adds the `link` console command and the `!link` chat command to the server game
module (new file `game_src/native/tcp_link.h`, three small hooks in `tcp_game.c`). It writes
`<fs_homepath>/<fs_game>/links/CODE.json` with the player's guid; the bot hashes the guid into the public
player id exactly like the stats service and deletes the file. Apply with `git apply` (core.autocrlf=false),
ship it in the next release, then update the official servers. `game/test_link_harness.c` drives the new code
with a fake engine and checks the file the bot reads.

## Development

```sh
python -m venv .venv && .venv/bin/pip install --require-hashes -r requirements.lock pytest
.venv/bin/python -m pytest -q
```

The tests build the whole command tree offline (Discord's limits on names, descriptions and options),
render every message with data produced by the real stats service code (`tests/fixtures/tcp_stats.py`
is a copy of `tools/server-bridge/tcp_stats.py`) against Discord's embed limits, and run the background jobs
(status cards, outage debounce, leader and match alerts, release drafts and publishing, linking, event
waitlists, match reports, seasons, alerts, map votes, the chat bridge, appeals) against fake channels.
The pickup queue and a full scrim run against a fake game server on real UDP.

## Look and feel (1.2.0)

- **Image cards.** `/profile`, `/top` and match reports post a drawn card in the game's HUD style
  (tcpbot/cards.py, Pillow, the website's own fonts in assets/fonts under the SIL Open Font License).
  Map art is read from the local site copy (`devlog.site_root`). If drawing ever fails, the bot posts the
  text version instead. Turn the cards off with `"cards": {"enabled": false}`.
- **Bot emoji.** The game's own rank insignia and team emblems (assets/game-icons, from the game's HUD
  pk3) plus medals and status lights are uploaded as application emoji on start (tcpbot/emoji.py). They
  belong to the bot, so they use none of the server's emoji slots. Changed art is re-uploaded by itself.
- **Colours with a meaning.** Green: match live. Amber: filling up. Grey: waiting for players. Red: offline.
  Spec Ops orange and Terrorist red on match cards, rank colours on profiles.
- **Server cards** show a player bar (players, bots, open slots), the round count and a Join server button.
- **Profile.** Banner and About me are set once per design change; the status line follows the busiest server.
- **Welcome and get-started** use Discord's newer layout (framed card with banner, choices and buttons).
