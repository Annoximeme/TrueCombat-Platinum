# Staff keys from the portal: server side (0.36.0)

`tcp_staff_filekeys.h` lets a dedicated server accept staff badge keys made in the staff portal on top
of the keys built into the game (`tcp_staff_keys.h`). The client does not change: the portal hands
staff a normal `TCPSTAFF1 <id> <seed>` key file.

Wire it into `tcp_staff.h`:

1. Include `tcp_staff_filekeys.h` right after the `staffBadge` / `staffKeyIndex` / `staffNonce` /
   `staffRequests` declarations (it uses `staffBadge`, `TCP_STAFF_KEYS`, `clients`, `playerConfig`, `print`).
2. `TCP_StaffClear(n)`: also `staffBadgeId[n][0]=0;`.
3. In `tcp_staffauth`, replace the lookup loop over `tcpStaffKeys` with
   ```c
   TCP_StaffLoadFile();
   const unsigned char *pub;const char *keyName;int role;
   if(!TCP_StaffFindKey(id,&pub,&keyName,&role)){TCP_StaffReject(n,"unknown_key");return 1;}
   ```
   then check the signature against `pub`, set `staffBadge[n]=role;` and
   `snprintf(staffBadgeId[n],sizeof(staffBadgeId[n]),"%s",id);`, and log `keyName` in TCP_STAFF_VERIFIED.
   `staffKeyIndex` can go, or stay -1 for file keys.
4. Register the cvar `g_staffKeyFile` (default `staffkeys/staffkeys.txt`, server only) with the other
   `g_staff*` cvars, and call `TCP_StaffLoadFile()` once at game init.
5. Console / rcon dispatch (next to `TCP_StaffAdminConsole`): `if(TCP_StaffKeysConsole(cmd))return 1;`
6. Add `tcp_staff_filekeys.h` to the files the build copies next to `tcp_staff.h`.

Checks: `staffkeys_reload` prints `TCP_STAFF_KEYS file=<n> builtin=<n> dropped=<n>`. A key listed in
the file verifies like a built-in one. After its line is removed, `staffkeys_reload` prints
`TCP_STAFF_REVOKED` and the orange name goes away. A server without the file works as before.

On the VPS, `install.sh install` creates `<home>/tcetest/staffkeys/` for each server, and the portal
keeps `staffkeys.txt` in it.
