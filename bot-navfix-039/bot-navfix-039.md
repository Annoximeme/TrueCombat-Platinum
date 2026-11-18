# Bot navigation fixes + sniper-scope freeze fix for the 0.39.0 rebuild (kit bot-navfix-039)

Thread "Make bots smarter in matches". Gianni approved putting these in the 0.39.0 rebuild ("All of them", 2026-11-18 12:45Z): the bot nav fixes without the ping replies (those wait for the 0.40 pings), plus the sniper-scope freeze fix.

## 1. Kit
Folder: /mnt/project-files/integ039/kits/bot-navfix-039/

| file | use |
|---|---|
| patches/01-bot-navfix.patch | Bot nav fixes, the same patch as the 0.40 kit (integ040/kits/bot-navfix). Files: tcp_bots.h, tcp_bot_nav.h, tcp_bot_obj.h, tcp_bot_smart.h, tcp_bot_vary.h. |
| patches/02-bot-lof-free.patch | The sniper-scope freeze fix. File: tcp_bot_tactics.h only. It does not depend on 01. |

For each one: `git apply -p1` at the repo root. CRLF is kept where the files use it. The sha256 values are in the SUMMARY.

Apply order:
1. The 0.39.0-sandbox37 source.
2. The community maps botflags patch (sha256 f1969535…, patch 02 of integ039/kits/community-polish).
3. 01.
4. 02.

01 also edits navNearest, the same function botflags edits, so botflags must go first.

**KIT GATE PASSED 2026-11-18 13:05Z** (kit checksum 777294561bd2ef1c): [bot-navfix-039/SUMMARY.md](bot-navfix-039/SUMMARY.md).
- The gate base was TrueCombat-Platinum-0.39.0-sandbox37-source.zip (sha256 20e7673f…) with botflags applied, packed as one zip.
- compose, Windows -Werror build, built-file scan, Linux server and bots soak (Village, Snow, Railhouse): pass.
- scan: the one known hit in the unmodified base (preflight_release.py comment), counted as passed per the release thread.
- The Windows probes were built but not run, because wine is broken in this container. Run them on the PC.

| patch | sha256 |
|---|---|
| 01-bot-navfix.patch | d15cf6164efb69f5fe21673eb1f26fd3e0d4865b71f1d20b3c04ef6cd6f5adf1 |
| 02-bot-lof-free.patch | 05b7c0115d43ae7bb3016a4e67a1a7913d4a1122e1158088b838a7cb7a8785d4 |

## 2. Extra build steps
None. The change is qagame only: no cgame, no paks, no protocol change.

New server cvars (archived):
- `bot_navfix 1` (0 = the 0.39.0 bot nav behaviour).
- `bot_smart_quiet 1` (0 = off).
- `bot_lof_free 1` (0 = the 0.38/0.39 behaviour).

## 3. What it fixes
**Sniper-scope freeze (02):**
- **The bug:** bots give way to a human teammate who aims (the line-of-fire rule from 0.38). In a corridor where a bot has no way out of the aim cone, the bot crouched and froze for 8 s. If you were still aiming, the next 8 s pause started straight away. So scoping in froze the bots in front of you until you unscoped.
- **Live versions:** this is in the published 0.38.x builds too.
- **The fix:**
  - A bot that cannot leave the cone now crouches below your aim and keeps moving.
  - After a dodge, it waits 4 s before dodging again for the same player. After an 8 s timeout, it waits 10 s.
- **Status counters:** the TACSTAT line gains `lof_timeouts` and `lof_boxed_walks`.

**Nav fixes (01):** the details are in integ040/kits/bot-navfix.md, section 3.
- Climb loops: these also caused the bomb carrier to flip-flop between sites.
- First-leg stuck (audit F6).
- Bots off the nav graph.
- Defuse and fetch role churn.
- Round-start route-planning hitch.
- Bots stuck inside a wall by the Railhouse ladder.
- Crawl-space start nodes.
- Bots step aside from a human teammate instead of standing inside him (flag carrier).
- Quiet movement near enemies.

## 4. Test checklist (in-game pass)
Columns: `map | renderer | cvars/commands | look at | pass rule | shot`

- obj_railhouse or obj_village | either | any team mode, bots on your team | scope in with a sniper down a corridor with bots ahead | bots keep moving (crouched if they cannot get out of the way); none stands still until you unscope | y
- obj_snow, obj_stadtrand | either | bomb mode, 12 bots | the carrier | goes to one site and plants; no back-and-forth | n
- obj_village | either | CTF, you take the flag and stand still | bots around you | no bot model inside your view | y
- any | either | g_perfSpike 8 | round start | round-start hitches not worse than 0.38.2 | n
- any | either | `bot_navfix 0; bot_smart_quiet 0; bot_lof_free 0` + map_restart | bots | same as before this kit | n

## 5. Cloud evidence
- **Nav fixes:** 48-run bench against the 0.39 bots: PASS.
  - Climb loops 677 down to 252.
  - Elimination kills 14.1 vs 11.1 per min.
  - CTF captures 3.2 vs 2.5.
  - Bomb plants 4.3 vs 3.8, stalls 3.5 vs 4.3.
  - Details in integ040/kits/bot-navfix.md.
- **Freeze fix:** a scoped stand-in teammate in a test build (TDM on Railhouse, Village and Snow, 4 min each).
  - Dodge episodes 323 down to 153; 787 boxed-in frames where bots now walk on instead of freezing.
  - Kills per minute went up on every map: Railhouse 17.0 to 20.5, Snow 14.5 to 18.8, Village 24.0 to 31.5.
  - Not yet seen with a real human scoping in.

## 6. Public patch notes lines (suggested)
- Bots no longer freeze in front of you while you aim down a scope. If they can't get out of your line of fire, they crouch and keep moving.
- Bots no longer get stuck climbing the same ledge over and over, and the bomb carrier no longer keeps switching between sites.
- Bots that got stuck at the start of their route, or ended up somewhere with no route (a roof, a pit by a ladder), now find their way out.
- Bots no longer stand inside you when you stop on a spot they were heading for (for example after taking the flag).
- One bot now keeps the defuse or bomb pickup job instead of two bots swapping it back and forth.
- Smoother round starts with many bots.
- Bots walk quietly when they know an enemy is close.
