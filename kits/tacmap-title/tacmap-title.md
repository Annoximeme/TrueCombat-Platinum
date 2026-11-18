# Map display names from the map data: "VILLA2 1" -> "VILLA 2.1" (tactical map, scoreboard, map vote)

Thread "Recover TC:E community maps". From the 0.39.1 queue: the Villa 2.1 tactical map title read "VILLA2 1". This is a cgame-only change to one file (tcp_mapvote_cg.h); there is no data, server or protocol change.

KIT GATE PASSED 2026-11-18 17:25Z on the FINAL 0.39.0 source zip (80320953...), all steps green: [SUMMARY.md](SUMMARY.md), kit checksum f965cf67dcb04d67.

## Cause
In 0.39.0, audit-polish patch 01 makes the tactical map, the scoreboard header and the map vote all use mapVotePretty(). That function builds the name from the file name: it drops "obj_", turns "_" into spaces and capitalises, so "obj_villa2_1" becomes "Villa2 1". The `title` line that the community map data (zz_community_mapdata.pk3) and Harbour's map data carry was only read by the loading screen.

## Fix (patches/01-map-title.patch, tcp_mapvote_cg.h)
New mapVoteDataTitle() reads the optional `title` line of gfx/platinum/maps/<map>.txt and drops a trailing " (...)". The result is cached per map (16 slots), so each file is read only once. mapVotePretty() uses it when present and falls back to the old rule otherwise. This one change covers all three places, because they all call mapVotePretty().

The stock maps' txt files have no `title` line, so their names do not change. Host test of the same function on the shipped txt files:

| map | name |
|---|---|
| obj_villa2_1 | Villa 2.1 |
| obj_shozen | Shozen |
| obj_snowtown | Snowtown |
| obj_chlite | Chlite |
| harbour | Harbour (drops " (Experimental)", same as today) |
| obj_village | Village (unchanged) |
| no txt | old rule |

The tactical map and scoreboard uppercase the result as before, so it shows VILLA 2.1.

| file | sha256 |
|---|---|
| patches/01-map-title.patch | 0ad804d1f06f400ea85b67e4ec587a360b8af4e41013804dbb9488a736710b57 |

Base: v0.39.0-sandbox37 source zip + integ039 kits audit-polish (01a-08) + parallax-repair patch 01, which is the 0.39.0 rebuild state of the cgame UI files. The file is CRLF, and the patch keeps CRLF. Re-check it on the final 0.39.0 source zip after publish. old-sandbox37/ holds a superseded first version, made for the base without audit-polish; do not use it.

## Public patch notes line
- Community map names now read properly on the tactical map, scoreboard and map vote (for example "Villa 2.1").

## Test checklist
- obj_villa2_1 | either | tactical map key + scoreboard | title | reads VILLA 2.1 | y
- server with map vote, community map in the list | either | end-of-match vote | names | Villa 2.1 / Shozen / Snowtown / Chlite | y
- obj_village, harbour | either | tactical map + vote | names | unchanged (VILLAGE, HARBOUR) | n
