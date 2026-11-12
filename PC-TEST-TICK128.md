# 128 Hz snapshot readiness test (tick128.patch)

Goal: prove that snaps 128 is safe for real players. Gianni chose "Work toward 128" on 2026-11-12.
Everything runs locally. Never touch the VPS or the live servers.

## What the patch changes (engine only, protocol 84 unchanged)
- PACKET_BACKUP 32 -> 64 (client and server snapshot rings). MAX_PARSE_ENTITIES 2048 -> 8192.
- The delta window is negotiated per client:
  - New clients send the userinfo key `snaphist 64` (a ROM cvar).
  - The server deltas from frames up to 61 old for those clients and up to 29 old for everyone else, as before.
- Rate cap 90000 -> 250000 B/s (TCP_MAX_RATE), matching the launcher's `rate 250000`. LAN clients get the same cap.

## Build
- Base: the newest next-release tree. Use the playtest036 private copy, or netfeel-0360 if that has landed.
- Apply on a COPY, never in playtest036 itself: `git apply -p1 --directory=<engine prefix if needed> tick128.patch`.
  - Paths are reference/etlegacy/src/...
  - The files are CRLF, and the patch is CRLF-faithful.
- Build client and server. Also keep an unpatched build of the same tree for A/B.

## Ports and lock
- UDP 28160-28164.
- Take C:\TrueCombatWork\suite.lock atomically (CreateNew) with the text "tick128 study, CPU-sensitive". Wait while someone else holds it.
- Delete the lock and stop all servers when done.

## Matrix
obj_village with 15 bots and 1 real client that moves and shoots (same driver as C:\TrueCombatWork\tickrate\tick_suite.ps1). 60 s measured per run.
- Link profiles (from the lag-sim proxy):
  - P1: 60 ms, 1% loss
  - P2: 150 ms, 2% loss
  - P3: 250 ms, 3% loss + 10% reorder
  - P4: 120 ms, with a 400 ms total-loss burst every 10 s
- For each profile run:
  - (a) unpatched, snaps 128
  - (b) patched, snaps 128
  - (c) patched, snaps 64
- Record per run:
  - snapshots/s received
  - non-delta (full) snapshots/s: cl_shownet 3 lines with delta:0, or server Com_DPrintf "Delta request from out of date packet" with developer 1
  - "Delta frame too old" / "Delta parseEntitiesNum too old" count
  - bytes/s per client (sv_showAverageBPS)
  - rate-limited skipped frames
  - prediction errors (cg_showmiss 1)
  - client fps, server CPU %
- Hit agreement: the lag sim A shoots B with 4 weapons under P3, patched snaps 128 vs patched snaps 64.

## Compatibility (must all pass)
1. Patched server + unpatched client at snaps 128 under P3: plays and no errors, and the server keeps that client on the 29-frame window. Check with developer 1: "out of date packet" may appear, "Delta frame too old" must not.
2. Unpatched server + patched client: plays normally.
3. Demo recorded by the patched client under P3 plays back in the patched client. Note whether the unpatched client can play it, which is informational only.
4. Server memory (RSS) with sv_maxclients 20 and 64, patched vs unpatched.

## Output
C:\TrueCombatWork\tick128\RESULTS.md with the tables above and a verdict: is snaps 128 safe at P1-P4?
