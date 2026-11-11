# Online play round 3: intake for the 0.35.0 candidate

## Patches

### Game and engine

- **File:** /mnt/project-files/online-play/round3/on-0.34.1/engine-game-round3.patch
- **sha256:** c9e5fdd60b87…
- **Format:** git diff, -p1 against the published 0.34.1 source root (f__source__native-sandbox-source.zip, tag v0.34.1-sandbox26). It applies with `git apply` (core.autocrlf=false), and CRLF line endings are preserved.
- **Version:** this already includes the two fixes from the PC test (ban dialog full stop, net graph uses the server-measured ping). Use this file, not the older 525e3403 copy plus round3-fix.patch under C:\TrueCombatWork\online-play\round3.

Files:
- game_src/native: tcp_game.c, tcp_cgame.c, tcp_stats.h, tcp_lagcomp.h, new tcp_netq.h, new tcp_netq_cg.h
- reference/etlegacy/src: server/sv_admin.c, server/sv_game.c, server/sv_net_chan.c, server/server.h, game/g_public.h

### Launcher

- My launcher changes (one-click join, IPv6, Verified tag) are already inside the launcher thread's combined /mnt/project-files/launcher-pass/launcher-1.5.0.patch (433effda).
- If that thread has moved to 2.0.0, it carries them. Do not apply the old launcher-join.patch (1.4.0) or on-0.34.1/launcher-1.5.0.patch on top: they are the same code, so it would double-apply.

## What the game and engine patch touches

### Server engine (needs the new platinum-server / etlded binary)

- Timed bans: `ban/banip/banguid <target> [30m|12h|7d|2w] reason`.
  - The banlist gets an `expires` field.
  - The reject dialog shows the time left.
  - banguid refuses duplicates.
- New optional trap `trap_TcpNetStats` (G_TCP_NETSTATS, found through G_TRAP_GETVALUE "trap_TcpNetStats"). An older engine returns 0 and the game simply has no loss numbers.
- client_t gains tcpNetReceived and tcpNetDropped, counted in sv_net_chan.c.

### qagame

tcp_netq.h, with hooks in tcp_game.c:
- loss, jitter and ping telemetry
- `tcp_nq` broadcast every 2 s (humans only)
- ping cap: g_maxPing 0 (off), g_maxPingTime 20, g_maxPingAction 0 = spectator / 1 = kick
- rejoin keeps team and score: g_reconnectKeep 300
- pickup teams: g_pugTeams 0 (userinfo tcp_team r|b)
- automatic cheat flags: g_cheatFlags 1, written to reports/*-auto-*.json (tcp-report/1, "auto": true)

Changes to existing files:
- tcp_stats.h: the match JSON adds `"leaves"` and `"net":{ping,pingMax,jitter,loss,rewind,rewindCapped,shotsRewound}` next to the existing "filler".
- tcp_lagcomp.h: records how far each shot was rewound.

### cgame

tcp_netq_cg.h:
- scoreboard connection icons next to the ping column
- cg_netGraph 0/1/2 (archived cvar)

### Not touched

- **Protocol:** stays 84, with no new snapshot fields. `tcp_nq` is a server command, so client and qagame must ship together, as they always do.
- **Paks, anticheat, acReleasePaks:** none of them, and no new assets.
- **Packaging:** only the rebuilt server binary, qagame, cgame and the launcher (from the launcher thread). Patch notes stay out of the package as usual.

### VPS side (stays out of the client release; needs Gianni's typed OK)

- Stats bridge redeploy (PR #39 code: leaver rating, abandons, /netstats.json, verified flag).
- New dual-stack master (platinum_master.c, in the launcher tree).
- ufw for IPv6 and IPV6=1 on the official servers.
- Ranked cfg: g_maxPing 180 and g_antilagMaxMs 200.
- AAAA DNS at Hostinger.
- The Discord bot's pickup.join_url is set after the release.

## PC test (2026-11-11, Gianni-PC, 8/8 PASS)

The test used a local server on UDP 28080 and two real clients (DX12 and OpenGL), from a test copy at C:\TrueCombatWork\online-play\round3\game.

Results: C:\TrueCombatWork\online-play\round3\PC-TEST-RESULTS.md. Screenshots are in run2\ and run3\; logs and match JSON are in run*\home-*.

| Check | What was tested | Result |
|---|---|---|
| a | Scoreboard icons | PASS |
| b | cg_netGraph 1 and 2 | PASS |
| c | Timed ban and its dialog (after the fix) | PASS |
| d | Ping cap | PASS |
| e | Rejoin keeps team and score | PASS |
| f | Pickup team lock | PASS |
| g | leaves and net in the match JSON | PASS |
| h | No crashes | PASS |

Automatic cheat flags were not exercised, because kills came from tcp_kill under devmap.

## PR #39 (website, bridge, server kit)

- Merged 2026-11-11 by Gianni's "Merge everything" (merge commit 90fae39).
- The website side is live now:
  - join.html in EN/NL;
  - Join links and the Verified tag in all five languages.
- The Join links need launcher 1.5.0+, and join.html says so.
- The bridge side only takes effect after the VPS redeploy.

## Patch-note lines (Discord-ready)

```
**Online play**
- One-click join: Join buttons on truecombat.eu and in Discord now open the game straight into the server, with the password and team already set.
- Full servers: the launcher waits for a free slot and joins you automatically.
- Connection check: before joining, the launcher tests your connection to the server and steadies unstable links automatically.
- New net graph: set cg_netGraph 1 for ping, packet loss and jitter, or 2 for a live ping graph.
- Connection bars next to every player's ping on the scoreboard.
- Rejoin protection: drop out and come back within five minutes to return to your team with your score intact.
- Ranked fairness: servers can set a ping limit, and leaving a ranked match you are losing now costs the full rating change.
- Server admins: timed bans (30m, 12h, 7d, 2w) that show players exactly when their ban ends.
- Server-side anomaly checks file reports for staff review.
- IPv6: servers and the server list now support IPv6.
```
