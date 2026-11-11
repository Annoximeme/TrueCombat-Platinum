"""Renders every message with data produced by the real stats service code
(tests/fixtures/tcp_stats.py is a copy of tools/server-bridge/tcp_stats.py),
and checks Discord's size limits."""

import datetime as dt
import importlib.util
import json
import pathlib
import random
import re

import discord
import pytest

from tcpbot import config, embeds
from tcpbot.sources import parse_devlog, parse_status

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("tcp_stats", HERE / "fixtures" / "tcp_stats.py")
tcp_stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcp_stats)


@pytest.fixture(scope="module")
def cfg(tmp_path_factory):
    p = tmp_path_factory.mktemp("cfg") / "config.json"
    p.write_text(json.dumps({"guild_id": 1, "channels": {"status": 1},
                             "servers": [{"key": "official1", "channel": 1},
                                         {"key": "official2", "name": "Official #2 Unranked", "port": 27961,
                                          "public_address": "2.24.59.195:27961", "match_type": "Unranked"}]}))
    return config.load(str(p))


@pytest.fixture(scope="module")
def stats():
    store = tcp_stats.StatsStore(min_matches=1)
    rng = random.Random(4)
    names = ["Gianni", "^1Red^7Fox", "*under_score*", "@everyone", "Ravo", "Sniper`Wolf", "Ghost", "Medic"]
    guids = ["%032X" % rng.getrandbits(128) for _ in names]
    start = dt.datetime(2026, 11, 7, 18, 0, tzinfo=dt.timezone.utc)
    for m in range(12):
        ended = start + dt.timedelta(minutes=25 * (m + 1))
        players = []
        for i, (n, g) in enumerate(zip(names, guids)):
            k = rng.randint(2, 25)
            players.append({"guid": g, "name": n, "team": "specops" if i % 2 else "terrorists", "kills": k,
                            "deaths": rng.randint(2, 20), "teamKills": 0, "headshots": rng.randint(0, k),
                            "damage": k * 110, "roundsWon": rng.randint(0, 6), "timePlayed": 1200,
                            "objectives": rng.randint(0, 2),
                            "weapons": {"M4": {"kills": k // 2, "shots": 300, "hits": 70, "headshots": 1},
                                        "MP5": {"kills": k - k // 2, "shots": 200, "hits": 40},
                                        "Knife": {"kills": 0}}})
        store.ingest({"schema": "tcp-match/1", "id": "m%d" % m, "server": "Official", "map": rng.choice(
            ["obj_snow", "obj_village", "obj_delta"]), "mode": "Team elimination", "practice": False,
            "started": (ended - dt.timedelta(minutes=20)).isoformat(), "ended": ended.isoformat(),
            "duration": 1200, "rounds": 10, "winner": rng.choice(["specops", "terrorists"]),
            "players": players}, "local", trusted=True)
    return store


LIMITS = {"title": 256, "description": 4096, "field.name": 256, "field.value": 1024, "footer": 2048, "total": 6000}


def check(e: discord.Embed):
    d = e.to_dict()
    total = len(d.get("title", "")) + len(d.get("description", "")) + len(d.get("footer", {}).get("text", ""))
    assert len(d.get("title", "")) <= LIMITS["title"]
    assert len(d.get("description", "")) <= LIMITS["description"]
    assert len(d.get("fields", [])) <= 25
    for f in d.get("fields", []):
        assert 0 < len(f["name"]) <= LIMITS["field.name"]
        assert 0 < len(f["value"]) <= LIMITS["field.value"], f
        total += len(f["name"]) + len(f["value"])
    assert total <= LIMITS["total"]
    # outside code blocks, player names are escaped (embeds never ping, but it keeps them literal)
    blob = re.sub(r"```.*?```", "", json.dumps(d, ensure_ascii=False), flags=re.S)
    assert "@everyone" not in blob
    return d


def status_packet(players):
    head = b"\xff\xff\xff\xffstatusResponse\n\\mapname\\obj_snow\\tcp_mode\\Team elimination\\sv_maxclients\\16" \
           b"\\tcp_version\\0.33.0\n"
    return head + b"".join(b'%d %d "%s"\n' % (s, p, n.encode()) for n, s, p in players)


def test_server_card_online_offline(cfg, stats):
    board = stats.leaderboard()
    status = parse_status(status_packet([("^1Red^7Fox", 12, 40), ("Gianni", 30, 25), ("[BOT]Ghost", 3, 0)]))
    servers = {"servers": [{"address": "1.2.3.4:27960", "players": 3}, {"address": "2.24.59.195:27961", "players": 0}]}
    d = check(embeds.server_card(cfg, cfg["servers"][0], status, board, servers, None))
    assert d["description"].startswith("**Online** · Ranked")
    fields = {f["name"]: f["value"] for f in d["fields"]}
    assert fields["Map"] == "Snow" and fields["Players"] == "2 / 16  ·  1 bot"
    assert fields["On the server"].index("Gianni") < fields["On the server"].index("RedFox")
    assert fields["Community servers"].startswith("1 online · 3 players")   # official #2 is not "community"
    assert d["image"]["url"].endswith("/img/maps/snow-hd.webp")
    assert d["footer"]["text"].startswith("Version 0.33.0")
    off = check(embeds.server_card(cfg, cfg["servers"][1], None, board, None, 1_700_000_000))
    assert off["description"].startswith("**Offline** since <t:1700000000:R>")


def test_profile_leaderboard_compare(cfg, stats):
    board = stats.leaderboard()
    for sort in ("rating", "xp", "kills", "kd", "headshots", "wins"):
        check(embeds.leaderboard(cfg, stats.leaderboard(sort=sort, limit=20), sort, "all"))
    a = stats.player(board["players"][0]["id"])
    b = stats.player(board["players"][1]["id"])
    d = check(embeds.profile(cfg, a))
    names = [f["name"] for f in d["fields"]]
    assert names[:6] == ["Skill rating", "Leaderboard", "Matches", "Kills / deaths", "Headshots", "Time played"]
    assert "Favourite weapons" in names and "Recent matches" in names
    assert "Knife" not in json.dumps(d)            # weapons without kills are left out
    check(embeds.compare(cfg, a, b))
    check(embeds.recent_matches(cfg, stats.recent()))
    check(embeds.new_leader(cfg, board["players"][0], board["players"][1]))
    empty = check(embeds.leaderboard(cfg, {"players": [], "minMatches": 1}, "rating", "30d"))
    assert "1 completed ranked match." in empty["description"]


def test_server_list(cfg):
    servers = {"servers": [{"address": "1.2.3.%d:27960" % i, "name": "^2Server %d" % i, "map": "obj_delta",
                            "mode": "Bomb", "players": i, "bots": 2, "maxPlayers": 16, "ranked": i % 2 == 0,
                            "password": i == 3} for i in range(14)]}
    d = check(embeds.server_list(cfg, servers))
    assert d["fields"][0]["name"] == "Server 13"
    assert d["fields"][-1]["value"].startswith("And 4 more")


RELEASE = {"id": 1, "tag_name": "v0.33.0-sandbox24", "html_url": "https://github.com/x/y/releases/tag/v0.33.0",
           "published_at": "2026-11-08T20:00:00Z",
           "assets": [{"name": "TrueCombat-Platinum-Setup.exe", "browser_download_url": "https://dl/setup.exe"}],
           "body": (HERE / "fixtures" / "release-body.md").read_text(encoding="utf-8")}


def test_release_announcement(cfg):
    d = check(embeds.release_announcement(cfg, RELEASE))
    assert d["title"] == "TrueCombat: Platinum 0.33.0 is out"
    names = [f["name"] for f in d["fields"]]
    assert names[0] == "ULTRA VISUALS (DIRECTX 12)"
    assert "DEVELOPMENT" not in names and names[-1] == "Get it"
    assert "https://dl/setup.exe" in d["fields"][-1]["value"]


def test_devlog(cfg):
    feed = (HERE / "fixtures" / "devlog.xml").read_text(encoding="utf-8")
    entries = parse_devlog(feed)
    assert entries and entries[0]["url"].startswith("https://truecombat.eu/devlog-")
    d = check(embeds.devlog_post(cfg, entries[0], "https://truecombat.eu/img/og.jpg"))
    assert d["author"]["name"].startswith("Devlog · ")


def test_event_card(cfg):
    from tcpbot.store import Store
    s = Store()
    eid = s.add_event("playtest", "0.34.0 playtest", "Bring a headset.", 1_900_000_000, 2, "2.24.59.195:27960", 1)
    for uid, st in ((1, "going"), (2, "going"), (3, "waitlist"), (4, "maybe")):
        s.rsvp(eid, uid, st)
    d = check(embeds.event_card(cfg, s.event(eid), s.rsvps(eid), "Gianni"))
    fields = {f["name"]: f["value"] for f in d["fields"]}
    assert fields["Going (2/2)"] == "<@1> <@2>" and fields["Waitlist (1)"] == "<@3>"
    assert d["author"]["name"] == "Playtest"
    assert "/connect 2.24.59.195:27960" in d["description"]
