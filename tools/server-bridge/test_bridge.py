#!/usr/bin/env python3
"""Loopback test: a fake master and two fake game servers on 127.0.0.1, then the bridge over HTTP."""
import json, pathlib, socket, struct, sys, tempfile, threading, time, urllib.request
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import tcp_bridge

OOB = b"\xff\xff\xff\xff"

def udp(handler):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(("127.0.0.1", 0))
    def run():
        while True:
            data, addr = s.recvfrom(4096)
            for reply in handler(data):
                s.sendto(reply, addr)
    threading.Thread(target=run, daemon=True).start()
    return s.getsockname()

def game(name, players, mode, extra=""):
    def h(data):
        if data == OOB + b"getstatus":
            info = "\\sv_hostname\\%s\\mapname\\obj_railhouse\\g_gametype\\3\\tcp_mode\\%s\\sv_maxclients\\16\\g_needpass\\0\\version\\TC Platinum 0.30.0%s" % (name, mode, extra)
            lines = "".join('%d %d "%s"\n' % (sc, pg, n) for n, sc, pg in players)
            yield OOB + ("statusResponse\n" + info + "\n" + lines).encode()
    return udp(h)

g1 = game("^1Red ^7Server", [("^2Gianni", 12, 30), ("Bob", 3, 55), ("Bot Hawk", 4, 0)], "Team elimination", "\\tcp_ranked\\1\\tcp_need\\1")
g2 = game("Quiet", [], "Practice")
dead = ("127.0.0.1", 9)  # listed but never answers

def master(data):
    if data.startswith(OOB + b"getservers 84"):
        body = b"".join(b"\\" + socket.inet_aton(ip) + struct.pack(">H", port) for ip, port in (g1, g2, dead))
        yield OOB + b"getserversResponse" + body + b"\\EOT\0\0\0"
m = udp(master)

stats = tempfile.mkdtemp()
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
for i in range(3):
    json.dump({"schema": "tcp-match/1", "ended": now, "map": "obj_railhouse", "mode": "Team elimination",
               "players": [{"guid": "AAA", "name": "Gianni", "kills": 10, "deaths": 2, "headshots": 4, "roundsWon": 3,
                            "weapons": {"M4": {"kills": 10}}},
                           {"guid": "BBB", "name": "Bob", "kills": 2, "deaths": 10, "headshots": 0, "roundsWon": 1}]},
              open(pathlib.Path(stats, "m%d.json" % i), "w"))
json.dump({"schema": "tcp-match/1", "ended": now, "practice": True, "players": [{"guid": "CCC", "kills": 99}]},
          open(pathlib.Path(stats, "practice.json"), "w"))

port = 18090
args = ["--master", "%s:%d" % m, "--listen", "127.0.0.1:%d" % port, "--stats-dir", stats, "--interval", "3600", "--cors", "*"]
threading.Thread(target=tcp_bridge.main, args=(args,), daemon=True).start()
time.sleep(5)
srv = json.load(urllib.request.urlopen("http://127.0.0.1:%d/servers.json" % port))
lb = json.load(urllib.request.urlopen("http://127.0.0.1:%d/leaderboard.json?period=30d" % port))
print(json.dumps(srv, indent=1)); print(json.dumps(lb, indent=1))
assert srv["master"]["online"] and srv["master"]["listed"] == 3
names = sorted(s["name"] for s in srv["servers"]); assert names == ["Quiet", "Red Server"], names
red = [s for s in srv["servers"] if s["name"] == "Red Server"][0]
assert red["players"] == 2 and red["maxPlayers"] == 16 and red["mode"] == "Team elimination" and red["playerList"][0]["name"] == "Gianni"
assert red["bots"] == 1 and red["ranked"] is True and len(red["playerList"]) == 2
quiet = [s for s in srv["servers"] if s["name"] == "Quiet"][0]
assert red["need"] == 1
assert quiet["bots"] == 0 and quiet["ranked"] is None and quiet["need"] == 0
assert lb["matches"] == 3 and [p["name"] for p in lb["players"]] == ["Gianni", "Bob"]
assert lb["players"][0]["kills"] == 30 and lb["players"][0]["topWeapon"] == "M4" and "guid" not in lb["players"][0]
print("bridge test passed")
