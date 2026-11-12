# F12 bug report upload: wire format `tcp-bugreport/1`

This is the contract between the game client (TrueCombat: Platinum 0.36.0 and later) and the staff portal receiver. The client always saves the report locally first. The upload is an extra step: if it fails, nothing is lost.

## Request

- **Method and URL:** `POST https://staff.truecombat.eu/api/bugreport`. The URL is the client cvar `cl_bugReportEndpoint`.
  - Only `https://` is accepted.
  - `http://` is accepted only for `127.0.0.1` and `localhost`, so a local test receiver can be used.
- **Headers:**
  - `Content-Type: application/json; charset=utf-8`
  - `User-Agent: TrueCombat-Platinum-BugReport/1`
- **Body:** one JSON object of at most 1.6 MB (1,638,400 bytes). The body is UTF-8 and plain ASCII on the wire: the client escapes any byte outside printable ASCII as `\u00XX`.
- **Authentication:** none. Abuse protection is the client rate limit plus the receiver's per-address limit (see Responses).

| Key | Type | Notes |
|---|---|---|
| `format` | string | Always `tcp-bugreport/1`. |
| `category` | string | `Bug`, `Suggestion` or `Feature`. The receiver treats it case-insensitively. |
| `text` | string | The player's description, 10 to 479 characters. The client enforces the 10-character minimum. |
| `map` | string | BSP name, e.g. `obj_railhouse`. Empty in the main menu. |
| `pos` | array of 3 numbers | The player's origin `[x, y, z]`. |
| `server` | string | `ip:port` of the server. Empty when offline or on the player's own listen server. |
| `server_name` | string | `sv_hostname` of that server. Empty when `server` is empty. Optional for the receiver. |
| `build` | string | The installed release from `<install>/manifest.json`, e.g. `0.36.0-sandbox28`. Falls back to the engine version string. |
| `protocol` | string | Native protocol, e.g. `tcp-native-capture-7`. Optional for the receiver. |
| `renderer` | string | `dx12` or `opengl1`. |
| `time` | number | Client clock as a Unix timestamp in seconds. |
| `ping` | number | Ping in ms at the moment of the report. |
| `fps` | number | Average frame rate over the last 32 frames. |
| `hw` | object | Present only when the player leaves "Include hardware info" ticked. A flat object of strings: `gpu`, `gpu_vendor`, `driver`, `resolution`, plus `cpu` and `memory_mb` when the engine knows them. Empty values are left out. At most 24 keys. |
| `console` | string | The last ~200 console lines, at most 48 KB. |
| `name` | string | Player name with colour codes kept, e.g. `^1Ex^7ample`. |
| `guid` | string | Raw `cl_guid` (32 hex). The portal hashes it before storing it. |
| `puid` | string | Easy Anti-Cheat / EOS product user id when the player is signed in, otherwise empty. |
| `match` | string | Match id of the server's round log (`tcp_matchid` in serverinfo, the id in `stats/<stamp>-<id>.json` and `stats/rounds/<id>-r<round>.json`). Empty when `server` is empty. |
| `screenshot_jpg` | string | Optional. Plain base64 (no `data:` prefix) of the JPEG taken when F12 was pressed. The JPEG is at most 1 MB. If the whole body would exceed 1.6 MB, the client leaves the screenshot out and keeps it locally. |

[`sample.json`](sample.json) is a valid example with made-up values and a tiny screenshot.

## Responses

| Status | Body | Client shows |
|---|---|---|
| `201` | `{"ok": true, "id": "<report id>"}` | "Report sent" |
| `400` | bad body, or `text` shorter than 10 characters | "Saved locally (upload failed)" |
| `413` | body over 1.6 MB | "Saved locally (upload failed)" |
| `429` | more than 6 reports per hour from one address | "Saved locally (upload failed)" |
| `503` | inbox full | "Saved locally (upload failed)" |

- Any 2xx status counts as sent. Anything else, or no answer within 20 s, counts as failed.
- The client does not retry. The report stays in `<profile>/tcetest/bugreports/`.

## Client behaviour

- **Opening a report:** F12 opens the report box (`bugreport` on the console). `bugreport <text>` files a `Bug` report with that text at once.
- **Sending:** "Enter: save" appears only once the text has at least 10 characters. Shorter text shows a counter instead and cannot be sent.
- **Rate limit:** one upload per 60 s per client. Reports in between are saved locally only.
- **Turning uploads off:** `cg_bugReportUpload 0` keeps every report local.
- **Changing the address:** set `cl_bugReportEndpoint` (not archived, so a test address never sticks).
