"""Personal alerts: who gets a DM, and how often."""

from tcpbot.cogs import alerts
from test_flows import FakeBot, make_cfg, run


class FakeUser:
    def __init__(self):
        self.dms = []

    async def send(self, **kw):
        self.dms.append(kw["embed"])


def make():
    cfg = make_cfg()
    bot = FakeBot(cfg, {})
    users = {1: FakeUser(), 2: FakeUser()}
    bot.get_user = users.get
    cog = alerts.Alerts.__new__(alerts.Alerts)
    cog.bot, cog.cfg, cog.ac, cog.online, cog.maps = bot, cfg, cfg["alerts"], {}, {}
    return cog, bot, users


def status(mapname, *names):
    return {"cvars": {"mapname": mapname}, "players": [{"name": n, "score": 0, "ping": 40} for n in names]}


def test_player_and_map_alerts_with_cooldown():
    cog, bot, users = make()
    server = cog.cfg["servers"][0]
    bot.store.alert_add(1, "player", alerts.name_key("^1Red^7Fox"), "RedFox")
    bot.store.alert_add(2, "map", "obj_snow", "Snow")
    run(cog.check_server(server, status("obj_village", "RedFox", "A")))      # first look after a restart: silent
    assert not users[1].dms
    run(cog.check_server(server, status("obj_village", "A")))
    run(cog.check_server(server, status("obj_village", "A", "^1Red^7Fox")))
    assert len(users[1].dms) == 1 and "RedFox" in users[1].dms[0].title
    run(cog.check_server(server, status("obj_village", "A")))
    run(cog.check_server(server, status("obj_snow", "A", "RedFox")))         # rejoin inside the cooldown
    assert len(users[1].dms) == 1
    assert len(users[2].dms) == 1 and "Snow" in users[2].dms[0].title
    run(cog.check_server(server, status("obj_delta")))
    run(cog.check_server(server, status("obj_snow")))                        # nobody playing: no map alert
    assert len(users[2].dms) == 1


def test_rank_alert_names_who_passed():
    cog, bot, users = make()
    bot.store.link(1, "a" * 16, "A")
    bot.store.alert_add(1, "rank", "self", "Leaderboard place")
    boards = []

    class S:
        async def leaderboard(self, *a, **k):
            return {"players": boards[-1]}
    bot.stats = S()

    def P(pid, name, rating):
        return {"id": pid * 16, "name": name, "rating": rating}
    boards.append([P("a", "A", 1200), P("b", "B", 1100), P("c", "C", 1000)])
    run(cog.check_ranks())
    assert not users[1].dms
    boards.append([P("b", "B", 1250), P("a", "A", 1200), P("c", "C", 1000)])
    run(cog.check_ranks())
    assert len(users[1].dms) == 1 and "B" in users[1].dms[0].description and "#2" in users[1].dms[0].description
    boards.append([P("b", "B", 1250), P("c", "C", 1230), P("a", "A", 1200)])
    run(cog.check_ranks())
    assert len(users[1].dms) == 1                                           # cooldown
