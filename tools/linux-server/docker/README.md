# TrueCombat: Platinum server in Docker

```sh
docker compose up -d          # first start downloads and verifies ~700 MB of game data
docker compose logs -f
```

Settings live in `compose.yaml` (`SERVER_NAME`, `MAX_PLAYERS`, `MODE`, `BOTS`, `RCON_PASSWORD`,
`SERVER_PASSWORD`, `MAX_PING`, `RECORD_DEMOS`, `DOWNLOAD_URL`, `LIST_PUBLICLY`, `MAP_ROTATION`,
`START_MAP`, `IPV6`). They are written to `/data/home/tcetest/server.cfg` on the first start; after that the
file is yours to edit (`REGENERATE_CONFIG=1` rewrites it from the environment).

Updating: `docker compose build --pull && docker compose up -d`. Unchanged game data is kept.

Custom maps: put the map `.pk3` files in any web folder (for example a static site or a Caddy
`file_server`) and set `DOWNLOAD_URL` to it. Players without the map download it when they join.

Running several servers: copy the service block with another name, port (`"27961:27961/udp"`,
`PORT: "27961"`) and volume.

IPv6: set `IPV6: "1"`. Docker only passes IPv6 traffic in when IPv6 is on for the daemon and the
network (`"ipv6": true` in `/etc/docker/daemon.json` plus an IPv6 network for the service), or when
the container runs with `network_mode: host`. IPv4 stays on either way.
