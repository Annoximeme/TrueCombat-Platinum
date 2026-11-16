"""/staff: the bot talks to the staff portal as the member who typed the command."""

import asyncio
import json
import types

import aiohttp
from aiohttp import web

from tcpbot.bot import UserFacingError
from tcpbot.cogs.staffportal import PortalAPI, headers_for


def member():
    roles = [types.SimpleNamespace(id=555), types.SimpleNamespace(id=777)]
    return types.SimpleNamespace(id=300000000000000003, roles=roles, display_name="Disc Mod")


def test_headers_carry_the_member_and_roles():
    h = headers_for(member(), "tok")
    assert h["X-Bot-Token"] == "tok" and h["X-Discord-Id"] == "300000000000000003"
    assert h["X-Discord-Roles"] == "555,777" and h["X-Discord-Name"] == "Disc%20Mod"


def test_portal_calls_and_errors():
    seen = []

    async def handler(request):
        seen.append((request.method, request.path, dict(request.headers), await request.text()))
        if request.path == "/bot/action":
            return web.json_response({"error": "Your role cannot do that."}, status=403)
        return web.json_response({"name": "Disc Mod", "role": "moderator"})

    async def go():
        app = web.Application()
        app.router.add_route("*", "/bot/{tail:.*}", handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        async with aiohttp.ClientSession() as s:
            api = PortalAPI(s, "http://127.0.0.1:%d/" % port, "tok")
            me = await api.call(member(), "GET", "me")
            try:
                await api.call(member(), "POST", "action", {"action": "ban"})
                refused = ""
            except UserFacingError as e:
                refused = str(e)
            off = PortalAPI(s, "http://127.0.0.1:%d" % port, "")
            try:
                await off.call(member(), "GET", "me")
                unlinked = ""
            except UserFacingError as e:
                unlinked = str(e)
            dead = PortalAPI(s, "http://127.0.0.1:9", "tok")
            try:
                await dead.call(member(), "GET", "me")
                down = ""
            except UserFacingError as e:
                down = str(e)
        await runner.cleanup()
        return me, refused, unlinked, down

    me, refused, unlinked, down = asyncio.run(go())
    assert me["role"] == "moderator"
    assert refused == "Your role cannot do that."
    assert "not linked" in unlinked
    assert "isn't answering" in down
    assert seen[0][2]["X-Bot-Token"] == "tok" and seen[1][0] == "POST" and json.loads(seen[1][3]) == {"action": "ban"}
