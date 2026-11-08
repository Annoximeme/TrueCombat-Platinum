# Linux dedicated server

Native x86_64 Linux build of the TrueCombat: Platinum dedicated server. No Wine.

| File | What it does |
| --- | --- |
| `build-linux-server.sh` | Builds `platinum-server.x86_64` (engine) and `qagame.mp.x86_64.so` (game module) from an unpacked release source snapshot. Needs cmake, ninja and clang. |
| `kit/` | What a server host gets: `install.sh` (fetches and verifies the game paks from the release), `start.sh`, a default `server.cfg`, a systemd unit and a README. |
| `update-server.sh` | Keeps servers on the newest release: waits until no human players are on, installs side by side, restarts, and switches back automatically if a server does not come up. |

## Releases

`.github/workflows/linux-server.yml` runs when a release is published. It
downloads that release's `f__source__*.zip`, builds both binaries, smoke-tests
them and attaches `TrueCombat-Platinum-Linux-Server.tar.gz` (+ `.sha256`) to
the same release. Releases whose source has no Linux support yet are skipped.
It can be re-run for any tag from the Actions tab.

## Build by hand

```sh
unzip f__source__native-sandbox-source.zip -d src
tools/linux-server/build-linux-server.sh src out
```

## Automatic updates on a server host

```
/opt/truecombat/
  current -> releases/<tag>    what the services run
  releases/<tag>/              the newest three releases
  home/tcetest/server.cfg      configs, logs, stats, demos (kept across releases)
```

Each service runs `/opt/truecombat/current/start.sh` with
`Environment=HOME_DIR=/opt/truecombat/home` (plus `PORT` / `CONFIG`). Then, from
cron or a systemd timer every 10 minutes:

```sh
update-server.sh /opt/truecombat truecombat-1 27960 truecombat-2 27961
```

Server demos (`sv_autoDemo`) go to `home/tcetest/svdemos`; `kit/prune-demos.sh` removes recordings older
than 14 days (run it daily from cron). For skill-based team balance, point the stats bridge at each
server's ratings file: `tcp_stats.py serve --ratings-file /opt/truecombat/home/tcetest/ratings.txt`.
