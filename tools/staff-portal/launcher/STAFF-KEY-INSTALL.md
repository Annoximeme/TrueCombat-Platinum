# Launcher: install a staff key from the staff portal (launcher 2.1, ships with 0.36.0)

In the staff portal, a staff member clicks their name › Staff badge in game › **Install in game**. The portal
opens a one-time link:

    truecombat://staffkey/<32 lowercase hex>

The code is valid for 10 minutes and works once. The launcher already owns `truecombat://`. On this link:

1. **Check the link.** Accept exactly `truecombat://staffkey/` followed by 32 characters `[0-9a-f]`
   (ignore a trailing `/`). Ignore anything else.
2. **Ask first.** Show: "Install your TrueCombat staff key on this PC? This replaces any staff key
   already installed." with Install / Cancel. A web page could open the link, so never install without this
   click.
3. **Make the key pair on this PC.**
   - `BCryptGenRandom(NULL, seed, 32, BCRYPT_USE_SYSTEM_PREFERRED_RNG)` for the seed.
   - Monocypher 4.0.2 (already in the game tree: `monocypher.c` and `monocypher-ed25519.c`) for the key pair:
     `crypto_ed25519_key_pair(secret_key, public_key, seed_copy)`.
   - That call wipes the seed you pass in, so pass a copy and keep the original 32-byte seed for the file.
4. **Claim the link.** Use the same HTTPS stack as the updater (WinHTTP, TLS only, fixed host). Never take the
   host from the link.

       POST https://staff.truecombat.eu/api/staffkey/claim
       Content-Type: application/json
       {"code": "<the 32 hex from the link>", "public": "<64 lowercase hex public key>"}

   | Answer | Meaning | Launcher shows |
   |---|---|---|
   | 201 `{"id": "k…", "name": "…"}` | done | go to step 5 |
   | 410 | link used or expired | "This link has expired. Make a new one in the staff portal." |
   | 403 | no staff access any more | "This account no longer has staff access." |
   | 429 | too many tries | "Too many tries. Try again later." |
   | other / no network | | "Could not reach the staff portal. Try again, or download the key in the portal." |

5. **Write the key.**
   - Write `TCPSTAFF1 <id> <64 lowercase hex seed>\r\n` (ASCII) to `<game install folder>\profile\staff.key`. This is the
     same file the download makes and the same folder the game reads.
   - Write to `staff.key.tmp` first, then `MoveFileExW(..., MOVEFILE_REPLACE_EXISTING)`.
   - Create `profile` if it is missing.
   - The game seals the key to the Windows account (DPAPI) the first time it reads it.
6. **Clean up.** Wipe the seed and secret key from memory (`crypto_wipe`). Show "Staff key installed. Start
   the game and join one of our servers." The portal page notices the new key by itself and shows it as
   installed.

Never log the seed, and never send it anywhere: only the public key leaves the PC.

Test against the live portal with a real staff account. Expect 201 the first time and 410 when the same link
is opened again. After that, staffkeys.txt on the VPS lists the new key id, and in 0.36.0 the badge shows
in game. Bump the launcher version and `platinum_launcher_version.h` as usual.
