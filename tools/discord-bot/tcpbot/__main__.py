"""Command line entry point.

  python -m tcpbot run        connect to Discord (what the service runs)
  python -m tcpbot check      validate the config file and exit
  python -m tcpbot preview    print the status cards and leaderboard as JSON, without Discord
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from . import __version__, config


def _logging(verbose: bool):
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s", stream=sys.stdout)
    logging.getLogger("discord").setLevel(logging.INFO if verbose else logging.WARNING)


def cmd_check(cfg) -> int:
    if cfg.problems:
        for p in cfg.problems:
            print("problem:", p)
        return 1
    print("config OK: %s" % cfg.path)
    return 0


async def _preview(cfg) -> int:
    import aiohttp

    from . import embeds
    from .sources import StatsAPI, StatsUnavailable, query_game

    async with aiohttp.ClientSession() as session:
        stats = StatsAPI(session, cfg["api_url"])
        try:
            board = await stats.leaderboard("rating", "all", 10)
            servers = await stats.servers()
        except StatsUnavailable:
            print("stats service unavailable at %s" % cfg["api_url"])
            board = servers = None
        out = []
        for server in cfg["servers"]:
            status = await query_game(server["host"], server["port"])
            out.append(embeds.server_card(cfg, server, status, board, servers, None).to_dict())
        if board:
            out.append(embeds.leaderboard(cfg, board, "rating", "all").to_dict())
        if servers:
            out.append(embeds.server_list(cfg, servers).to_dict())
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def cmd_run(cfg) -> int:
    from .bot import TCPBot
    from .store import Store

    if cfg.problems:
        cmd_check(cfg)
        return 1
    token = config.read_token()
    store = Store(cfg["state_db"])
    bot = TCPBot(cfg, store)
    import discord

    try:
        bot.run(token, log_handler=None)
    except discord.LoginFailure:
        print("error: Discord rejected the bot token. Reset it in the Developer Portal and store the new one "
              "with install.sh --token-stdin.", file=sys.stderr)
        return 1
    except discord.PrivilegedIntentsRequired:
        print("error: turn on Server Members Intent in the Developer Portal (Bot page), then restart.",
              file=sys.stderr)
        return 1
    finally:
        store.close()
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="tcpbot", description="TrueCombat: Platinum Discord bot %s" % __version__)
    ap.add_argument("command", choices=("run", "check", "preview"))
    ap.add_argument("--config", help="config file (default /etc/tcp-discord-bot/config.json)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    _logging(args.verbose)
    try:
        cfg = config.load(args.config)
        if args.command == "check":
            return cmd_check(cfg)
        if args.command == "preview":
            return asyncio.run(_preview(cfg))
        return cmd_run(cfg)
    except config.ConfigError as e:
        print("error:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
