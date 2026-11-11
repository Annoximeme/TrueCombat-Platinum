"""Every message the bot posts is built here, so the voice and look stay
consistent. Builders are pure: they take data and return discord.Embed
objects, which the tests and the preview command render without Discord.
"""

from __future__ import annotations

import datetime as dt

import discord

from . import achievements as A
from . import text as T
from .sources import is_bot, release_download, release_version

# Brand palette, taken from the website (docs/style.css)
RED = 0xD63B3B       # launcher PLAY red
AMBER = 0xE7A73C     # HUD compass lamp
GREEN = 0x4FBF7A
STEEL = 0x262E3B
GOLD = 0xC9A227
BLUE = 0x5B9BD5

FOOTER = "TrueCombat: Platinum"


def _now():
    return dt.datetime.now(dt.timezone.utc)


def _brand(embed: discord.Embed, text: str = FOOTER, stamp: bool = True) -> discord.Embed:
    embed.set_footer(text=text)
    if stamp:
        embed.timestamp = _now()
    return embed


def profile_url(site: str, pid: str) -> str:
    return "%s/player.html?id=%s" % (site, pid)


# ================================================================ server cards
def server_card(cfg, server: dict, status: dict | None, board: dict | None, servers: dict | None,
                offline_since: int | None) -> discord.Embed:
    site = cfg.site
    addr = server["public_address"]
    e = discord.Embed(title=server["name"], url=site + "/servers.html")
    pattern = cfg["bot_name_pattern"]
    footer = "Live · updated every minute"

    if status:
        cv, players = status["cvars"], status["players"]
        humans = [p for p in players if not is_bot(p, pattern)]
        bots = len(players) - len(humans)
        try:
            maxp = int(cv.get("sv_maxclients", "0")) - int(cv.get("sv_privateclients", "0") or 0)
        except ValueError:
            maxp = 0
        full = bool(maxp) and len(players) >= maxp
        mname = cv.get("mapname", "")
        mode = T.clean(cv.get("tcp_mode", ""), 32) or "-"
        version = T.clean(cv.get("tcp_version", ""), 32)
        kind = T.clean(server.get("match_type") or "", 60)
        e.colour = AMBER if full else GREEN
        state = "Server full" if full else "Online"
        e.description = "**%s**%s\n`/connect %s`" % (state, " · " + kind if kind else "", addr)
        count = "%d / %d" % (len(humans), maxp) if maxp else str(len(humans))
        if bots:
            count += "  ·  %d bot%s" % (bots, "" if bots == 1 else "s")
        e.add_field(name="Map", value=T.map_label(mname), inline=True)
        e.add_field(name="Mode", value=mode, inline=True)
        e.add_field(name="Players", value=count, inline=True)
        if humans:
            rows = sorted(humans, key=lambda p: -p["score"])[:16]
            body = T.table([(p["name"], p["score"], "%d ms" % p["ping"]) for p in rows], "lrr")
            e.add_field(name="On the server", value="```\n%s\n```" % T.clip(body, 990), inline=False)
        img = T.map_image(site, mname)
        if img:
            e.set_image(url=img)
        if version:
            footer = "Version %s · %s" % (version, footer)
    else:
        e.colour = RED
        since = offline_since or int(_now().timestamp())
        e.description = ("**Offline** since <t:%d:R>\nThe server is restarting or down for maintenance. "
                         "This card updates by itself when it is back." % since)

    top = int(cfg["status"].get("top_players") or 0)
    if top and board and board.get("players"):
        lines = ["`%d.` [%s](%s) · %s · %s" % (
            p["position"], T.md(p["name"]), profile_url(site, p["id"]), T.num(p["rating"]), p["rank"]["title"])
            for p in board["players"][:top]]
        e.add_field(name="Top of the leaderboard", value="\n".join(lines)[:1024], inline=False)

    if cfg["status"].get("show_community") and servers is not None:
        mine = {s["public_address"] for s in cfg["servers"]} | {"%s:%s" % (s["host"], s["port"]) for s in cfg["servers"]}
        others = [s for s in servers.get("servers", []) if s.get("address") not in mine]
        if others:
            total = sum(s.get("players", 0) for s in others)
            value = "%d online · %d player%s · [Browse the server list](%s/servers.html)" % (
                len(others), total, "" if total == 1 else "s", site)
        else:
            value = "None online right now · [Host your own](%s/guide.html)" % site
        e.add_field(name="Community servers", value=value, inline=False)
    return _brand(e, footer)


def how_to_join(cfg, server: dict) -> discord.Embed:
    addr = server["public_address"]
    e = discord.Embed(title="Join %s" % server["name"], colour=RED)
    e.description = (
        "**From the launcher**\nOpen the **Servers** tab, find the server in the list and press **Join**.\n\n"
        "**From the game console**\nPress `~` and enter:\n```\n/connect %s\n```"
        "Don't have the game yet? [Download TrueCombat: Platinum](%s/#download)." % (addr, cfg.site))
    return e


# ================================================================ feed
def new_leader(cfg, new: dict, old: dict | None) -> discord.Embed:
    e = discord.Embed(title="New #1 on the leaderboard", url=profile_url(cfg.site, new["id"]), colour=GOLD)
    desc = "**%s** takes the top spot with a skill rating of **%s**" % (T.md(new["name"]), T.num(new["rating"]))
    desc += ", overtaking **%s**." % T.md(old["name"]) if old else "."
    e.description = desc
    e.add_field(name="Rank", value=new["rank"]["title"], inline=True)
    e.add_field(name="Matches", value=T.num(new.get("matches")), inline=True)
    e.add_field(name="K/D", value=str(new.get("kd", 0)), inline=True)
    if new.get("topWeapon"):
        e.add_field(name="Weapon of choice", value=new["topWeapon"], inline=True)
    return _brand(e, "Full standings at truecombat.eu/leaderboards")


def match_on(cfg, server: dict, status: dict, humans: int) -> discord.Embed:
    mname = status["cvars"].get("mapname", "")
    e = discord.Embed(title="Match on now", url=cfg.site + "/servers.html", colour=RED)
    e.description = "**%d players** are fighting on **%s** on %s.\n`/connect %s`" % (
        humans, T.map_label(mname), T.md(server["name"]), server["public_address"])
    img = T.map_image(cfg.site, mname)
    if img:
        e.set_thumbnail(url=img)
    return _brand(e, "Get these alerts with the Match alerts role")


# ================================================================ stats
def profile(cfg, p: dict, member: discord.abc.User | None = None, unlocked: dict | None = None) -> discord.Embed:
    site = cfg.site
    rank = p["rank"]
    e = discord.Embed(title=T.md(T.clean(p["name"])), url=profile_url(site, p["id"]), colour=RED)
    if member is not None:
        e.set_author(name=member.display_name, icon_url=member.display_avatar.url)

    lines = ["**%s**  ·  Level %d" % (rank["title"], rank["level"])]
    if rank.get("xpNext"):
        lines.append("`%s`  %s / %s XP" % (T.progress_bar(rank["xp"], rank["xpThis"], rank["xpNext"]),
                                           T.num(rank["xp"]), T.num(rank["xpNext"])))
    else:
        lines.append("`%s`  %s XP · highest rank" % (T.progress_bar(1, 0, 1), T.num(rank["xp"])))
    e.description = "\n".join(lines)

    rating = T.num(p["rating"])
    if p.get("peakRating") and p["peakRating"] > p["rating"]:
        rating += "  (peak %s)" % T.num(p["peakRating"])
    e.add_field(name="Skill rating", value=rating, inline=True)
    e.add_field(name="Leaderboard", value=("#%d" % p["position"]) if p.get("position") else "Unranked", inline=True)
    e.add_field(name="Matches", value="%s  ·  %s won" % (T.num(p["matches"]), T.pct(p.get("wins", 0), p["matches"])),
                inline=True)
    e.add_field(name="Kills / deaths", value="%s / %s  ·  %s K/D" % (T.num(p["kills"]), T.num(p["deaths"]), p["kd"]),
                inline=True)
    e.add_field(name="Headshots", value="%s  ·  %s of kills" % (T.num(p["headshots"]), T.pct(p["headshots"], p["kills"])),
                inline=True)
    e.add_field(name="Time played", value=T.duration(p.get("timePlayed")), inline=True)

    weapons = [w for w in p.get("weapons") or [] if w.get("kills")][:3]
    if weapons:
        rows = [(w["name"], "%s kills" % T.num(w["kills"]),
                 ("%d%% acc" % round(100 * w["accuracy"])) if w.get("accuracy") is not None else "")
                for w in weapons]
        e.add_field(name="Favourite weapons", value="```\n%s\n```" % T.table(rows, "lrr"), inline=False)

    recent = (p.get("recent") or [])[:5]
    if recent:
        rows = [("W" if m["won"] else "L", T.map_label(m["map"]), "%d-%d" % (m["kills"], m["deaths"]),
                 T.signed(m["ratingChange"])) for m in recent]
        e.add_field(name="Recent matches", value="```\n%s\n```" % T.table(rows, "llrr"), inline=False)
    elif not p.get("matches"):
        e.add_field(name="Recent matches", value="No ranked matches yet. Play on a ranked server to get on the board.",
                    inline=False)
    if unlocked:
        best = A.best_first(unlocked)
        e.add_field(name="Achievements · %d of %d" % (len(best), len(A.ALL)),
                    value=T.clip("  ".join(A.label(k) for k in best[:6]), 1000) +
                    ("\nSee them all with `/achievements`." if len(best) > 6 else ""), inline=False)
    return _brand(e, "Full profile on truecombat.eu")


def leaderboard(cfg, board: dict, sort: str, period: str) -> discord.Embed:
    label = T.SORT_LABELS.get(sort, "Skill rating")
    title = "Leaderboard · %s%s" % (label, " · last 30 days" if period == "30d" else "")
    e = discord.Embed(title=title, url=cfg.site + "/leaderboards.html", colour=RED)
    players = board.get("players") or []
    if not players:
        e.description = "Nobody has qualified yet. A player appears after %d completed ranked match%s." % (
            board.get("minMatches", 1), "" if board.get("minMatches", 1) == 1 else "es")
        return _brand(e)

    def value(p):
        return {"rating": T.num(p["rating"]), "xp": T.num(p["rank"]["xp"]), "kills": T.num(p["kills"]),
                "kd": "%.2f" % p["kd"], "headshots": T.num(p["headshots"]), "wins": T.num(p["wins"])}[sort]

    rows = [("#", "Player", label.split(" ")[0], "Rank")] + [
        (str(p["position"]), T.clean(p["name"], 20), value(p), p["rank"]["short"]) for p in players]
    e.description = "```\n%s\n```" % T.table(rows, "rlrl")
    top = players[0]
    e.add_field(name="Leader", value="[%s](%s) · %s" % (T.md(top["name"]), profile_url(cfg.site, top["id"]),
                                                       top["rank"]["title"]), inline=True)
    e.add_field(name="Matches counted", value=T.num(board.get("matches")), inline=True)
    return _brand(e, "Full standings at truecombat.eu/leaderboards")


def server_list(cfg, data: dict) -> discord.Embed:
    servers = sorted(data.get("servers") or [], key=lambda s: (-s.get("players", 0), s.get("name", "")))
    total = sum(s.get("players", 0) for s in servers)
    e = discord.Embed(title="Servers online", url=cfg.site + "/servers.html", colour=GREEN if servers else STEEL)
    if not servers:
        e.description = "No servers are online right now."
        return _brand(e)
    e.description = "**%d** server%s · **%d** player%s in game" % (
        len(servers), "" if len(servers) == 1 else "s", total, "" if total == 1 else "s")
    for s in servers[:10]:
        badges = []
        if s.get("ranked"):
            badges.append("Ranked")
        if s.get("password"):
            badges.append("Password")
        players = "%d/%d" % (s.get("players", 0), s.get("maxPlayers", 0))
        if s.get("bots"):
            players += " +%d bots" % s["bots"]
        e.add_field(
            name=T.clip(T.clean(s.get("name"), 80) or s["address"], 256),
            value="%s · %s · %s%s\n`/connect %s`" % (T.map_label(s.get("map")), T.clean(s.get("mode"), 32) or "-",
                                                     players, (" · " + ", ".join(badges)) if badges else "",
                                                     s["address"]),
            inline=False)
    if len(servers) > 10:
        e.add_field(name="​", value="And %d more on the [server list](%s/servers.html)." % (
            len(servers) - 10, cfg.site), inline=False)
    return _brand(e)


def compare(cfg, a: dict, b: dict) -> discord.Embed:
    e = discord.Embed(title="%s vs %s" % (T.clean(a["name"]), T.clean(b["name"])), colour=RED)

    def hs(p):
        return T.pct(p["headshots"], p["kills"])

    rows = [
        ("Skill rating", a["rating"], b["rating"], T.num),
        ("Rank level", a["rank"]["level"], b["rank"]["level"], str),
        ("Matches", a["matches"], b["matches"], T.num),
        ("Win rate", (a.get("wins", 0) / a["matches"]) if a["matches"] else 0,
         (b.get("wins", 0) / b["matches"]) if b["matches"] else 0, lambda v: "%d%%" % round(100 * v)),
        ("K/D", a["kd"], b["kd"], lambda v: "%.2f" % v),
        ("Kills", a["kills"], b["kills"], T.num),
        ("Headshot %", (a["headshots"] / a["kills"]) if a["kills"] else 0,
         (b["headshots"] / b["kills"]) if b["kills"] else 0, lambda v: "%d%%" % round(100 * v)),
    ]
    table = [("", T.clean(a["name"], 14), T.clean(b["name"], 14))]
    score = [0, 0]
    for label, va, vb, fmt in rows:
        ma = "▸" if va > vb else " "
        mb = "▸" if vb > va else " "
        score[0] += va > vb
        score[1] += vb > va
        table.append((label, "%s %s" % (ma, fmt(va)), "%s %s" % (mb, fmt(vb))))
    e.description = "```\n%s\n```" % T.table(table, "lrr")
    if score[0] != score[1]:
        lead = a if score[0] > score[1] else b
        e.add_field(name="Edge", value="**%s** leads in %d of %d categories." % (
            T.md(lead["name"]), max(score), len(rows)), inline=False)
    else:
        e.add_field(name="Edge", value="Dead even.", inline=False)
    return _brand(e)


def recent_matches(cfg, data: dict) -> discord.Embed:
    e = discord.Embed(title="Latest ranked matches", url=cfg.site + "/leaderboards.html", colour=RED)
    matches = (data or {}).get("matches") or []
    if not matches:
        e.description = "No ranked matches have been played yet."
        return _brand(e)
    lines = []
    for m in matches[:8]:
        when = T.iso_to_unix(m.get("ended"))
        mvp = (" · MVP **%s** (%d kills)" % (T.md(m["mvp"]["name"]), m["mvp"]["kills"])) if m.get("mvp") else ""
        lines.append("**%s** · %s · %d players · %s%s" % (
            T.map_label(m.get("map")), T.clean(m.get("mode"), 32) or "-", m.get("players", 0),
            ("<t:%d:R>" % when) if when else "", mvp))
    e.description = "\n".join(lines)
    return _brand(e)


# ================================================================ linking
def link_instructions(code: str, minutes: int) -> discord.Embed:
    e = discord.Embed(title="Link your game profile", colour=RED)
    e.description = (
        "Join any official server and enter this in the game console (`~`):\n"
        "```\n/link %s\n```"
        "You can also type `!link %s` in chat. Nobody else sees the code.\n\n"
        "The code works once and expires <t:%d:R>. This message updates as soon as the server confirms."
        % (code, code, int(_now().timestamp()) + minutes * 60))
    e.set_footer(text="Linking is optional. Your rank and stats stay tied to your game key file either way.")
    return e


def link_done(cfg, name: str, pid: str) -> discord.Embed:
    e = discord.Embed(title="Profile linked", colour=GREEN, url=profile_url(cfg.site, pid))
    e.description = ("Your Discord account is now linked to **%s**. Your rank role will appear within a few "
                     "minutes, and `/profile` shows your stats without a name." % T.md(name))
    return e


# ================================================================ releases & devlog
def release_announcement(cfg, rel: dict) -> discord.Embed:
    version = release_version(rel)
    parsed = T.parse_release_body(rel.get("body") or "")
    e = discord.Embed(title="TrueCombat: Platinum %s is out" % version, url=rel.get("html_url"), colour=RED)
    intro = parsed["intro"] or "A new update is ready to download."
    e.description = T.clip(intro, 1200)
    shown = 0
    for sec in parsed["sections"]:
        if sec["title"].upper() in ("DEVELOPMENT",) or not sec["items"]:
            continue
        if shown >= 6:
            break
        items = sec["items"][:4]
        more = len(sec["items"]) - len(items)
        value = "\n".join("• " + T.clip(i, 160) for i in items)
        if more > 0:
            value += "\n• *and %d more*" % more
        e.add_field(name=sec["title"],
                    value=T.clip(value, 1024), inline=False)
        shown += 1
    e.add_field(name="Get it", value="The launcher updates itself on the next start. New players: [download the "
                "installer](%s) · [full patch notes](%s)" % (release_download(rel), cfg.site + "/news.html"),
                inline=False)
    return _brand(e, "Version %s" % version)


def devlog_post(cfg, article: dict, image: str | None) -> discord.Embed:
    e = discord.Embed(title=article["title"], url=article["url"], colour=AMBER)
    e.description = T.clip(article["summary"], 600) + "\n\n[Read the full article](%s)" % article["url"]
    e.set_author(name="Devlog" + (" · " + article["category"] if article.get("category") else ""))
    if image:
        e.set_image(url=image)
    return _brand(e, "Behind the scenes at Team Terminus")


def release_draft_notice(cfg, rel: dict, has_notes: bool) -> str:
    version = release_version(rel)
    if has_notes:
        return ("**%s** was published on GitHub. The announcement below is ready for the announcements "
                "channel, followed by the full patch notes." % version)
    return ("**%s** was published on GitHub. The announcement below is ready for the announcements channel. "
            "Use **Add patch notes** to attach the Discord patch notes first, or publish it as it is." % version)


# ================================================================ community
def welcome(cfg, member: discord.Member) -> discord.Embed:
    e = discord.Embed(colour=RED)
    e.title = "Welcome to the front, %s" % member.display_name
    e.description = (
        "TrueCombat: Platinum is the modern return of TrueCombat: Elite, the tactical shooter "
        "built on Wolfenstein: Enemy Territory. Here is how to get into a match:")
    e.add_field(name="1 · Install", value="[Download the installer](%s/#download). The launcher keeps the game "
                "up to date for you." % cfg.site, inline=False)
    e.add_field(name="2 · Learn the basics", value="Start with the [player guide](%s/guide.html), then warm up "
                "against bots with **Practice** in the launcher." % cfg.site, inline=False)
    e.add_field(name="3 · Find a match", value="`/servers` shows who is playing right now, and the **Match alerts** "
                "role pings you when a game is filling up.", inline=False)
    e.add_field(name="4 · Make it yours", value="`/link` connects your game profile to Discord for your rank "
                "role and `/profile`.", inline=False)
    e.set_thumbnail(url=member.display_avatar.url)
    return _brand(e, stamp=False)


def onboarding_panel(cfg) -> discord.Embed:
    e = discord.Embed(title="Get set up", colour=RED)
    e.description = (
        "Pick what you want to hear about. You can change this any time.\n\n"
        "**Match alerts** · a ping when a match is filling up on an official server\n"
        "**Playtester** · early builds and playtest sessions before a release\n"
        "**Event alerts** · scrims, community nights and tournaments\n\n"
        "Link your game profile with `/link` to get your rank role.")
    return _brand(e, stamp=False)


def event_card(cfg, ev, rsvps: dict[str, list[int]], host: str | None = None) -> discord.Embed:
    kind = ev["kind"]
    colour = AMBER if kind == "playtest" else RED
    label = "Playtest" if kind == "playtest" else "Event"
    e = discord.Embed(title=ev["title"], colour=colour if ev["state"] == "open" else STEEL)
    e.set_author(name=label + (" · closed" if ev["state"] != "open" else ""))
    desc = ev["description"].strip()
    when = "<t:%d:F> · <t:%d:R>" % (ev["starts"], ev["starts"])
    e.description = (desc + "\n\n" if desc else "") + "**When** " + when
    if ev["server"]:
        e.description += "\n**Server** `/connect %s`" % ev["server"]
    going, maybe, wait = rsvps.get("going", []), rsvps.get("maybe", []), rsvps.get("waitlist", [])
    cap = ev["capacity"]
    head = "Going (%d%s)" % (len(going), "/%d" % cap if cap else "")
    e.add_field(name=head, value=_mentions(going), inline=True)
    e.add_field(name="Maybe (%d)" % len(maybe), value=_mentions(maybe), inline=True)
    if wait:
        e.add_field(name="Waitlist (%d)" % len(wait), value=_mentions(wait), inline=True)
    footer = "%s #%d" % (label, ev["id"])
    if host:
        footer += " · hosted by %s" % host
    e.set_footer(text=footer)
    return e


# ---------------------------------------------------------------- matches, recap, seasons
TEAM_LABELS = {"specops": "Special Ops", "terrorists": "Terrorists", "red": "Red", "blue": "Blue",
               "axis": "Terrorists", "allies": "Special Ops"}


def team_label(key: str | None) -> str:
    return TEAM_LABELS.get(str(key or "").lower(), (key or "").title() or "Team")


def match_report(cfg, row: dict, detail: dict | None, unlocked: list[tuple[str, str]] | None = None,
                 mentions: dict[str, int] | None = None) -> discord.Embed:
    """A finished match. `row` is the entry from recent matches; `detail` the full scoreboard when the
    stats service has it. `unlocked` is [(player name, achievement key)], `mentions` maps player id to member."""
    m = detail or row
    mentions = mentions or {}
    e = discord.Embed(title="Match report · %s" % T.map_label(m.get("map")), colour=GOLD,
                      url=(cfg.site + "/match.html?id=%s" % row["id"]) if detail and row.get("id")
                      else cfg.site + "/leaderboards.html")
    img = T.map_image(cfg.site, m.get("map"))
    if img:
        e.set_thumbnail(url=img)
    head = []
    rounds = (detail or {}).get("score") or {}
    winner = m.get("winner")
    if winner and len(rounds) == 2 and winner in rounds:
        other = next(k for k in rounds if k != winner)
        head.append("**%s win %d – %d**" % (team_label(winner), rounds[winner], rounds[other]))
    elif winner and str(winner).lower() not in ("", "draw", "none"):
        head.append("**%s win**" % team_label(winner))
    else:
        head.append("**Draw**")
    if m.get("rounds"):
        head.append("%d rounds" % m["rounds"])
    if m.get("duration"):
        head.append(T.duration(m["duration"]))
    lines = [" · ".join(head)]
    sub = [x for x in (m.get("mode"), T.clean(m.get("server"), 60)) if x]
    if sub:
        lines.append(" · ".join(sub))
    ended = T.iso_to_unix(m.get("ended"))
    if ended:
        lines.append("Finished <t:%d:R>" % ended)
    e.description = "\n".join(lines)

    players = (detail or {}).get("players") or []
    if players:
        teams: dict[str, list[dict]] = {}
        for p in players:
            teams.setdefault(p.get("team") or "", []).append(p)
        order = sorted(teams, key=lambda t: (t != winner, t))
        for t in order[:2]:
            rows = [(T.clean(p["name"], 16), "%d-%d" % (p["kills"], p["deaths"]), T.signed(p["ratingChange"]))
                    for p in sorted(teams[t], key=lambda p: (-p["kills"], p["deaths"]))[:8]]
            e.add_field(name=team_label(t), value="```\n%s\n```" % T.table(rows, "lrr"), inline=True)
        best = max(players, key=lambda p: (p.get("xp") or 0, p["kills"]))
        who = "<@%d>" % mentions[best["id"]] if best["id"] in mentions else "[%s](%s)" % (
            T.md(best["name"]), profile_url(cfg.site, best["id"]))
        bits = ["%d kills" % best["kills"]]
        if best.get("headshots"):
            bits.append("%d headshots" % best["headshots"])
        if best.get("objectives"):
            bits.append("%d objective%s" % (best["objectives"], "" if best["objectives"] == 1 else "s"))
        if best.get("topWeapon"):
            bits.append(best["topWeapon"])
        e.add_field(name="Player of the match", value="%s · %s" % (who, ", ".join(bits)), inline=False)
    elif row.get("mvp"):
        e.add_field(name="Player of the match", value="[%s](%s) · %d kills" % (
            T.md(row["mvp"]["name"]), profile_url(cfg.site, row["mvp"]["id"]), row["mvp"]["kills"]), inline=False)
    if unlocked:
        text = "\n".join("%s · **%s**" % (A.label(k), T.md(n)) for n, k in unlocked[:10])
        if len(unlocked) > 10:
            text += "\n+%d more" % (len(unlocked) - 10)
        e.add_field(name="Achievements unlocked", value=T.clip(text, 1024), inline=False)
    return _brand(e, stamp=False)


def weekly_recap(cfg, r: dict) -> discord.Embed:
    days = r.get("days", 7)
    e = discord.Embed(title="The week in TrueCombat" if days == 7 else "The last %d days in TrueCombat" % days,
                      colour=RED, url=cfg.site + "/leaderboards.html")
    if not r.get("matches"):
        e.description = "A quiet one: no ranked matches were finished. The servers are up, bring a friend."
        return _brand(e)
    parts = ["**%s** matches" % T.num(r["matches"]), "**%s** players" % T.num(r["players"]),
             "**%s** played" % T.duration(r.get("timePlayed"))]
    line2 = ["%s kills" % T.num(r.get("kills")), "%s by headshot" % T.pct(r.get("headshots", 0), r.get("kills", 0))]
    if r.get("newPlayers"):
        line2.append("%s new player%s" % (T.num(r["newPlayers"]), "" if r["newPlayers"] == 1 else "s"))
    e.description = " · ".join(parts) + "\n" + " · ".join(line2)

    def who(x):
        return "[%s](%s)" % (T.md(x["name"]), profile_url(cfg.site, x["id"]))

    awards = [("mostKills", "Most kills", lambda x: "%s kills" % T.num(int(x["value"]))),
              ("mostWins", "Most wins", lambda x: "%d wins" % int(x["value"])),
              ("bestKd", "Best K/D", lambda x: "%.2f over %d matches" % (x["value"], x["matches"])),
              ("biggestClimb", "Biggest climb", lambda x: "%s rating" % T.signed(int(round(x["value"])))),
              ("mostObjectives", "Objective specialist", lambda x: "%d objectives" % int(x["value"])),
              ("mostActive", "Most active", lambda x: "%d matches" % int(x["value"]))]
    for key, title, fmt in awards:
        x = r.get(key)
        if x and (key != "biggestClimb" or x["value"] > 0):
            e.add_field(name=title, value="%s\n%s" % (who(x), fmt(x)), inline=True)
    if r.get("maps"):
        e.add_field(name="Most played maps", value=" · ".join(
            "%s (%d)" % (T.map_label(x["map"]), x["matches"]) for x in r["maps"]), inline=False)
    return _brand(e, "Every ranked match counts · truecombat.eu/leaderboards")


def season_board(cfg, board: dict, season: dict, final: bool = False, champion: int | None = None) -> discord.Embed:
    title = ("%s · final standings" if final else "%s · standings") % season["name"]
    e = discord.Embed(title=title, url=cfg.site + "/leaderboards.html", colour=GOLD if final else RED)
    players = [p for p in board.get("players") or [] if p.get("periodXp")]
    if not players:
        e.description = ("Nobody has played a ranked match this season yet. The first match puts you on top."
                         if not final else "No ranked matches were played this season.")
    else:
        rows = [("#", "Player", "XP", "Wins", "Rating")] + [
            (str(i), T.clean(p["name"], 18), T.num(p["periodXp"]), str(p.get("wins", 0)), T.signed(p.get("ratingGain", 0)))
            for i, p in enumerate(players, 1)]
        e.description = "```\n%s\n```" % T.table(rows, "rlrrr")
        top = players[0]
        who = "<@%d>" % champion if champion else "[%s](%s)" % (T.md(top["name"]), profile_url(cfg.site, top["id"]))
        e.add_field(name="Season champion" if final else "In the lead", value=who, inline=True)
    if final:
        e.add_field(name="Next season", value="Already under way. Everyone starts from zero.", inline=True)
    else:
        e.add_field(name="Season ends", value="<t:%d:R>" % season["end_ts"], inline=True)
    return _brand(e, "Season points are the XP you earn in ranked matches during the season", stamp=False)


def achievements_card(cfg, p: dict, unlocked: dict[str, int]) -> discord.Embed:
    e = discord.Embed(title="%s · achievements" % T.md(T.clean(p["name"])), url=profile_url(cfg.site, p["id"]),
                      colour=GOLD)
    have = A.best_first(unlocked)
    e.description = "**%d of %d** unlocked" % (len(have), len(A.ALL))
    if have:
        e.add_field(name="Unlocked", value=T.clip("\n".join(
            "%s · %s" % (A.label(k), A.ALL[k][1]) for k in have), 1024), inline=False)
    todo = [k for k in A.ALL if k not in unlocked][:5]
    if todo:
        e.add_field(name="Next up", value="\n".join("**%s** · %s" % (A.ALL[k][0], A.ALL[k][1]) for k in todo), inline=False)
    return _brand(e, stamp=False)


def _mentions(ids: list[int], limit: int = 30) -> str:
    if not ids:
        return "—"
    shown = " ".join("<@%d>" % i for i in ids[:limit])
    if len(ids) > limit:
        shown += " +%d" % (len(ids) - limit)
    return shown[:1024]


def notice(title: str, body: str, colour: int = RED) -> discord.Embed:
    return discord.Embed(title=title, description=body, colour=colour)


def error(body: str) -> discord.Embed:
    return discord.Embed(description=body, colour=STEEL)
