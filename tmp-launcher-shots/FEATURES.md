# TrueCombat: Platinum launcher 2.1.0

These are captures and the page list for the launcher that ships with game 0.36.0 and 0.36.1.
The page list comes from the 2.1.0 source (release_src/platinum_launcher.c and platinum_main.h, platinum_pages.h, platinum_shell.h).

## Version strings shown

- Bottom of the side rail: "Game 0.36.1", "Launcher 2.1.0", "Up to date".
- Play page headline: "VERSION 0.36.1-sandbox29", with an "UP TO DATE" chip.
- Settings > Updates: "Game: Version 0.36.1 · Up to date" and "Launcher: Version 2.1.0".
- File version of TrueCombatPlatinum.exe: 2.1.0.

## Captures

Every image is a lossless PNG at the launcher's native 1280x800 window size, at 100% interface size.

| File | Page |
|---|---|
| launcher-play.png | Play (hero) |
| launcher-servers.png | Servers, with the two official servers listed |
| launcher-settings-graphics.png | Settings > Graphics (quality preset, resolution, display mode) |
| launcher-profile.png | Profile |
| launcher-host.png | Host a server |
| launcher-settings-controls.png | Settings > Controls (player name, name colours, key bindings) |
| launcher-settings-launcher.png | Settings > Launcher (behaviour, appearance, updates, language) |
| launcher-replays.png | Replays |

The player name is the default, "Player". No staff features, keys or admin tools are visible. The update strip uses the launcher's own preview mode, so no update check or self-update ran.

## Pages

The side rail holds Play, Servers, News, Profile, Replays, Host a server and Settings. Below them are Support, the update status, and the game and launcher versions.

### Play
- One large PLAY button. It installs, updates, shows download progress or starts the game, depending on the state.
- A drop-down beside it offers Safe start, which uses OpenGL instead of DirectX 12.
- Three modes:
  - Quick play joins the best server right now.
  - Join by address.
  - Offline practice against bots.
- "Jump back in" cards hold your recent servers. Free slots offer Browse servers, Practice offline and Host a server.
- News cards: patch notes for this version, finding a match on Discord, and supporting the servers.
- Buttons for the patch notes and the trailer.
- Player strip: your name and your current graphics summary (preset, resolution, renderer).
- A "What's new" panel appears once after the game has been updated.

### Servers
- A live list from the master server, with server name, map, mode, players (and bots) and ping.
- "This PC" always appears first.
- Filter chips: Hide full, Hide empty, Ranked, No bots.
- Sort by any column. Favourites are marked with a star.
- Quick play and Refresh.
- When no public server answers, it offers Host a server, Practice offline and Try again.

### News
- Patch notes for the latest release, and a list of earlier updates.

### Profile
- Name, avatar initial and rank badge (Unranked until the stats service has ranked matches).
- Rank, K/D and match history, from the stats service.
- Change name.
- Player identity is a key file on this PC, with no account and no e-mail. You can back it up and restore it from the backup.
- Recent matches (recorded automatically) and Open profile folder.

### Replays
- Every map played is recorded automatically.
- F8 in game saves the last 30 seconds as a clip.
- Lists recorded matches and clips, and has Open folder.

### Host a server
- Your server: name, map preview, map, mode, player slots, bots and public list setting.
- Modes: Practice, Elimination, Team elimination, Point capture, Team deathmatch, Flag capture, Bomb.
- Maps: Railhouse, Northport, Delta, Stadtrand, Snow, Village.
- Start and stop the server. It keeps running after the launcher closes.
- Ranked status: server operators ask the team for a ranked key on Discord.
- Port-forwarding help for playing over the internet (UDP 27971), and a Server files button.

### Settings
Settings has six tabs.

- **Launcher**
  - When the game starts: Launcher window (Close the launcher, Minimize to tray or Keep it open), Come back after the match, Open on (start page), Start with Windows (in the tray).
  - Appearance: accent colour (5 swatches), Play page background (Rotate maps), interface size (90 to 150%), animations.
  - Updates: update the game automatically, update the launcher automatically, download speed limit.
  - Language: Automatic, English, German, French or Polish.
- **Graphics**
  - Quality preset: Low, High, Ultra or Custom.
  - Resolution, display mode (windowed, borderless or fullscreen) and vertical sync.
  - Every graphics option, which covers textures, shadows, anti-aliasing and DX12 effects.
  - Graphics report: GPU, driver and DirectX 12 support.
  - Launch options and Save for the next launch.
- **Controls**
  - Key bindings (Change keys).
  - Player name, Name colours (colour each letter of your name) and Profile and replays.
- **Updates**
  - Installed version: switch to an older release or back to the latest.
  - Game version with Check again, Patch notes, and Verify and repair.
  - Launcher version with Check now.
  - The same automatic update toggles and download speed limit as on the Launcher tab.
- **Privacy**
  - Player identity (a key file, no account, no e-mail).
  - Usage tracking: none.
  - Discord Rich Presence, update notifications (a Windows notification, never a pop-up), crash reports (only with approval, kept on this PC).
- **Storage**
  - Game folder and Move the game (to another folder or drive).
  - Disk use, Clear caches (shader cache and leftovers).
  - Screenshots, replays and settings (profile folder).
  - Server hosting files.

## Not captured

- **News:** it stays empty in capture mode, which is offline.
- **Name colour picker:** it's a separate dialog, and capture mode only renders it through an on-screen copy.
- **Every graphics option window:** same reason as the name colour picker.
- **Open Quality preset drop-down:** opening it needs input.

The Settings > Graphics capture shows the preset row with its description ("Low, High, Ultra or your own Custom mix"). The Controls capture shows the Name colours entry.
