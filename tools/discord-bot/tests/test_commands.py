"""Builds the whole command tree offline: catches invalid names, descriptions,
choices and autocomplete wiring before Discord would reject them."""

import asyncio
import json
import pathlib
import tempfile

from tcpbot import config
from tcpbot.bot import EXTENSIONS, TCPBot
from tcpbot.store import Store


def make_cfg():
    d = tempfile.mkdtemp()
    p = pathlib.Path(d) / "config.json"
    p.write_text(json.dumps({"guild_id": 123, "channels": {"status": 1}}))
    return config.load(str(p))


def test_command_tree_builds():
    async def go():
        cfg = make_cfg()
        bot = TCPBot(cfg, Store())
        for ext in EXTENSIONS:
            await bot.load_extension(ext)
        payloads = [c.to_dict(bot.tree) for c in bot.tree.get_commands()]
        for cog in list(bot.cogs.values()):
            await bot.remove_cog(cog.qualified_name)
        return payloads

    payloads = asyncio.run(go())
    names = sorted(p["name"] for p in payloads)
    assert names == sorted(["compare", "event", "events", "help", "link", "link-admin", "matches", "notify", "pickup", "admin",
                            "profile", "release", "servers", "setup", "top", "unlink",
                            "season", "recap", "achievements", "alerts", "team", "scrim", "tournament", "bug",
                            "suggest", "suggestion", "mapvote", "chat", "mod", "appeal", "ask", "account"]), names
    for p in payloads:
        assert 1 <= len(p["description"]) <= 100, p["name"]
        for o in p.get("options", []):
            assert len(o["description"]) <= 100, (p["name"], o["name"])
            for sub in o.get("options", []):
                assert len(sub["description"]) <= 100, (p["name"], o["name"], sub["name"])
    staff = {p["name"]: p.get("default_member_permissions") for p in payloads}
    assert staff["release"] and staff["setup"] and staff["event"] and staff["link-admin"] and staff["admin"]
    assert staff["account"] and staff["profile"] is None and staff["mod"] and staff["mapvote"] and staff["team"] is None
    assert len(payloads) <= 100
