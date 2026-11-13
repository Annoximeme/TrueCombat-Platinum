# Player accounts

Optional accounts for TrueCombat: Platinum. Nobody needs one to play. A player who signs in with Discord gets:

1. **Progress that follows them.** Every PC they link adds to one record in the stats service: one rank, one
   rating history, one set of totals. A new PC or a lost key never resets it: link the new PC and everything is back.
2. **A public profile** at `truecombat.eu/u/<name>` (`player.html?u=<name>`), with their Discord name only if they
   turn it on.
3. **A reserved name.** Official servers keep the name for its owner, look-alikes included.

`tcp_accounts.py` is the whole service: Python 3.10+ standard library, one SQLite file. Tests: `python3 test_accounts.py`
(103 checks; needs the `cryptography` package to sign like the launcher, the service itself does not).

## Identity

A PC is identified by the game's private Ed25519 key, `profile/etmain/eacid.key`, the key the game already uses for
the Easy Anti-Cheat sign-in. We never see the private key. The **key id** is the first 40 hex digits of SHA-256 of
the 32-byte public key, the same value as the `sub` of the EOS sign-in service.

`cl_guid` is not used for accounts: it is MD5 of `etkey`, every server sees it, and `etkey` can be rebuilt from it.

## How the parts talk

| From | To | What |
| --- | --- | --- |
| Website (`account.html`) | accounts | Discord sign-in, name, settings, link codes, export, delete |
| Launcher | accounts | `POST /api/account/claim`: signs a link code with `eacid.key` |
| Accounts | stats service | `POST /staff/accounts/aliases` (loopback, own token): which key ids are one account, and when |
| Accounts | game servers on the VPS | writes `<home>/tcetest/accounts/names.txt` (reserved names) |
| Game server | stats service | match reports carry the verified `key` per player (game 0.37.0) |
| Stats service | accounts | the answer to the alias push: when each account last played (keeps its name reserved) |
| Discord bot, staff portal | accounts | `GET /internal/lookup?discord=|name=|pid=` (loopback, `X-Accounts-Token`) |

## Routes

All public routes sit under `/api/account/` on **truecombat.eu** itself (a Caddy `handle`), so the session cookie
(`__Host-tcpacct`, HttpOnly, Secure, SameSite=Lax, 30 days) is first-party. Writes need the `X-CSRF` header from
`/me` and are refused from another Origin.

| Route | Who | Does |
| --- | --- | --- |
| `GET login`, `GET callback` | browser | Discord OAuth, scope `identify` only. The Discord token is thrown away after one `/users/@me`. |
| `GET me` | page | signed-in state, account, linked PCs, CSRF token |
| `GET check?name=` | page | is a name free and allowed |
| `POST signup` `{name, visibility, age13}` | page | creates the account and reserves the name |
| `POST name` `{name}` | page | rename: once per 30 days, old name held 30 days; respelling the same name is free |
| `POST settings` `{visibility?, showDiscord?}` | page | public/hidden profile, show Discord name |
| `POST link/start` → `{code, url}` | page | one-time code, 10 minutes; `url` = `truecombat://account/<code>` |
| `GET link/status?code=` | page | `waiting`, `linked`, `expired` |
| `POST claim` `{code, public, signature, label}` | launcher | links the key (hex public key, hex Ed25519 signature) |
| `POST unlink` `{key}` | page | the PC stops counting from now on; matches before stay with the account |
| `GET export` | page | everything about the account as a JSON download |
| `POST delete` `{confirm: name}` | page | removes account, keys, names, sessions, sign-in log |
| `GET profile?u=` | anyone | public profile (name, stats id, Discord if shown) |
| `GET names.json` | anyone | stats id -> account name, public accounts only |
| `GET reserved.txt` | game servers elsewhere | the reserved list (same as `names.txt`) |

## Progress follows you (stats service)

`tools/server-bridge/tcp_stats.py`:

* A tcp-match/2 player with `"key": "<40 hex>"` is filed under `player_id("key:" + key)` instead of the guid id.
* **Learned keys:** a verified match that shows a guid together with a key records the pair (table `guid_keys`),
  and the guid's whole history moves onto the key, so nobody loses what they earned before 0.37.0. A guid seen with
  several keys moves only when those keys are one player (linked to the same account at some time). Otherwise it moves
  to nobody and goes to the review queue: a copied guid cannot carry someone else's history to another key.
* **Aliases** from the account service map a key id to the account's stats id (`player_id("acct:" + account id)`) for
  the time it was linked (`since`, `until`). A change rebuilds the stats (`recompute`).
* Two ids of one player in the same match each keep their own id for that match and go to the review queue.
* Reports are stored with the ids they arrived with (`pid0`), so a rebuild applies the current links again.
* `export_ratings` writes every own id of a merged player with the merged rating, so `g_balanceSkill` still finds them.
* The answer to an alias push carries `seen`: the last match of each account's stats id. The account service counts it
  as activity.

## Reserved names

* 3 to 20 characters after colour codes: letters, digits, space and `- _ . [ ] * |`.
* Compared by a **skeleton**: NFKC, lower case, `0`=o `1 l !`=i `3`=e `4 @`=a `5 $`=s `7`=t `8`=b `9 6`=g `2`=z,
  separators dropped, repeated letters once. `RaziC*`, `r4z1c`, `R a z i c` and `Raazic` collide.
* Blocked: studio and staff words anywhere (admin, staff, moderator, official, truecombat, terminus, console, server,
  support, anticheat, devteam), some whole names (mod, gm, dev, owner, system, ...), anything starting with `player`
  (the game's fallback names), and a short abuse list.
* A name with no sign-in and no match for 12 months is released (the account stays). The next sign-in takes it back
  if nobody has claimed it meanwhile; otherwise the account page asks for a new one. A released name is not shown on
  leaderboards (`names.json`).

`names.txt` (also `GET /api/account/reserved.txt`):

```
TCPNAMES2 <unix time written>
<32 hex: sha256("tcp-name:" + skeleton)[:32]> <key tag>,<key tag>   ("-" = nobody may use it)
```

key tag = `sha256("tcp-namekey:" + key id)[:24]` hex. Only hashes are listed: the file names no account, and its key
tags cannot be matched to anyone's stats id (a key's stats id is derived from the key id itself). The file is written
mode 0644 into a setgid `tcpgame` folder.

## Game and launcher (0.37.0)

Nothing here ships in 0.36.0.

**Game server (qagame)**, reusing the staff-badge challenge code and Monocypher already in the game:

1. After the first snapshot the server sends `tcp_idchal <nonce>` (32 random hex). The client answers
   `tcp_idauth <public hex> <signature hex>`, signature = Ed25519 over
   `"TrueCombat identity v1\n" + nonce + "\n" + <cl_currentServerIP>`. Same flood-protect timing as the staff badge.
2. A good answer sets the client's verified key id. The tcp-match/2 writer adds `"key": "<key id>"` to that player.
3. Every 60 s the server re-reads `tcetest/accounts/names.txt` if its mtime changed. On connect, on a name change and
   when the key is verified: skeleton the clean name (same rules as `skeleton()` here; a C test vector file is
   generated from `test_accounts.py`), hash it, and if the hash is listed and the client's verified key is not in its
   list (compare `key_tag(verified key id)`), rename the client to `Player` + 4 digits and print one line: "That name is reserved by its owner." A client
   that has not answered the challenge within 10 s counts as unverified.

**Client (cgame/engine):** answer `tcp_idchal` with `eacid.key` (already loaded for EOS).

**Launcher 2.2.0:** handle `truecombat://account/<32 hex>`: show "Link this PC to your TrueCombat account?" with
Link / Cancel, then sign `"TrueCombat account link v1\n" + code + "\n" + <public hex>` with `eacid.key` and POST
`{code, public, signature, label}` to `https://truecombat.eu/api/account/claim`; `label` = the Windows computer name
unless the player edits it. Show the account name from the answer. Bump `platinum_launcher_version.h`.

## Deploy (VPS)

Needs Gianni's typed go. From the PC: copy `tools/accounts` to the VPS, then

```
sudo ./deploy/install.sh inspect       # port 8095 free? stats code has the alias route? secret present?
sudo ./deploy/install.sh install       # user tcpaccounts, /opt/tcp/accounts, tcp-accounts.service on 127.0.0.1:8095
sudo ./deploy/install.sh stats-link    # token + tcp-bridge drop-in 70-accounts.conf, restarts tcp-bridge
sudo ./deploy/install.sh caddy         # /api/account/* and /u/<name> in the truecombat.eu block (backup + validate)
```

The VPS stats code is **not** a main checkout: patch the `tcp_stats.py` hunks from this change into
`/opt/tcp/server-bridge`, never copy main over it. Back up `stats.db` first; the first alias push rebuilds the stats.

The Discord app is the staff portal's (client id 1569008112407683072); its redirect list has
`https://truecombat.eu/api/account/callback`. The client secret is copied from the staff portal on install.

If the site's Content-Security-Policy header limits `connect-src`, it must include `'self'`.

## Launch checklist (with 0.37.0)

1. Privacy page: a section on accounts (what is kept, why, how long, export and delete) in all five languages.
2. Nav: an *Account* entry; devlog post; roadmap item moves to shipped.
3. Official servers on 0.37.0 (key challenge + reserved names), launcher 2.2.0 live.
4. Discord bot reads Discord links from `/internal/lookup` (no in-game `/link` code needed for account holders).
