# Kit: audit-fixes (game audit round 2, on 0.38.1)

Owner thread: "Audit the whole game for bugs". Kit folder: /mnt/project-files/game-audit/round2/kit/
(patches/01-bomb-round-fixes.patch, 02-cqb-health-fix.patch, 03-small-fixes.patch). Plain `git apply`, CRLF kept.
Apply in name order. 01 and 02 stand alone; 03 needs 01 (neighbouring lines in tcp_game.c).
Gate summary: kit/SUMMARY.md next to the patches (base v0.38.1-sandbox35, bots soak in Bomb mode on Village + Snow).
Combined check 2026-11-18 00:32Z: all three apply, in order, on 0.38.1 + every 0.39 kit hunk in the touched files
(bot-smart, cqb-split, holster-gear, spectate-anim, immersion2, focus-zoom, community-maps, play-fixes 02).

Target: 01 = 0.39.0 late blocker (integrator's decision 00:27Z, live Ranked bug). 02 and 03 = next release unless Gianni
says otherwise.

## 01-bomb-round-fixes (tcp_game.c, tcp_cgame.c, tcp_qol_cg.h)
1. Double round result on detonation. explode() calls tickRound() on every kill; during the bomb blast that re-entered
   the round logic with bombState already 3, so "no Terrorist alive and bomb not planted" gave SpecOps the round, or
   "no SpecOps alive" gave Terrorists the round, and then the outer tickBomb() returned RED and scored again.
   Fix: bombBlast flag set around the blast; tickRound() returns at once while it is set.
2. Blast owner. The detonation used g.owner=0: kills, team kills and friendly-fire immunity for client 0.
   Fix: bombPlanter (set in plantBomb, cleared on new round and when that client leaves). The blast spares nobody;
   the planter is credited only for enemies it kills; everybody else dies with killer -1 and no suicide is counted.
3. Only Terrorists arm the bomb: team check in plantBomb(), tcp_select, the selected-weapon check and the weapon bit.
4. Kill feed and death card texts for deaths without a killer: 15 bomb ("was killed by the bomb", "KILLED BY THE BOMB"),
   31 water ("drowned"), 36 fall, 0 /kill ("killed himself"). Before: fall showed "Killed by your own blast", /kill showed
   "Fell to your death".

In-game checks: plant, stand next to the charge as Terrorist and as SpecOps at detonation: one round result, Terrorists +1,
feed says "was killed by the bomb" (own team) or "<planter> <<< you" (enemy of the planter). As SpecOps pick the dropped
bomb up: no bomb in the weapon list, fire does nothing at a site. Fall to death: card says "FELL TO YOUR DEATH".
Patch notes: "Bomb rounds are no longer scored twice when the explosion takes someone with it." "The bomb's explosion now
hurts everyone nearby and counts for the player who planted it." "SpecOps can no longer plant a bomb they picked up."

## 02-cqb-health-fix (tcp_cqb_g.h, tcp_game.c) - CQB Rules only
Health = f(head, body, legs damage totals), recomputed on every hit. Regeneration and Protected/Tank wrote health only,
so the next hit recomputed from the old totals and took everything back.
Fix: cqbHeal() lowers the totals (body, legs, head) until the formula gives the new health; the armour perks re-apply
the same hit with scaled damage instead of handing health back afterwards (cqbArmor -> cqbArmorScale).
Test (devmap harbour, tcp_native_rounds 7, g_experimental 1, tcp_cqbhurt): before 100-40=59, regen 64, -1 = 58;
after 59, 64, 63.

## 03-small-fixes (tcp_game.c, tcp_bot_tactics.h, tcp_smoke_fx.h, engine server/sv_voip.c)
- Blocked rotating door: hold step = real frame time, not 50 ms (door ran backwards at sv_fps above 20).
- New round: grenades in flight and smoke clouds of the old round are removed (log TCP_NATIVE_ROUNDCLEAR).
- botTacReach: no write to seen[-1].
- func_bobbing period at least 50 ms; welcome and server prints end in a real newline; smokeRand without signed overflow.
- sv_voip.c: elapsed clamped before the token product (overflow after about 10 h of silence).

## Not in this kit (handed to their owners)
Bot climb loops, carrier flip-flop, first-leg nav stuck: bot thread, data in NOTES.md (F6, F12).
