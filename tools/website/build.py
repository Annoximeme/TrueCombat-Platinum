#!/usr/bin/env python3
"""Builds the shared parts of the TrueCombat: Platinum website in docs/.

The English pages in docs/*.html are hand-edited. This script:
  1. rewrites the navigation, footer and language links between the
     <!--nav-->, <!--footer--> and <!--alt--> markers on every page,
  2. writes the weapon cards on weapons.html from weapons.json and the
     home page roadmap from roadmap.json (columns follow the latest release),
  3. writes the Dutch pages in docs/nl/ from the English ones plus the
     translations in nl.py (it stops with an error when an English
     string it needs is no longer on the page),
  4. writes the devlog: one page per post in devlog/<slug>.en.md and
     .nl.md (docs/devlog-<slug>.html and docs/nl/...), plus the post list
     between the <!--devlog--> markers on devlog.html,
  5. writes docs/sitemap.xml.

Run it after changing any English page:   python tools/website/build.py
"""
import html as htmlmod
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
HERE = pathlib.Path(__file__).resolve().parent
SITE = "https://truecombat.eu/"
DISCORD = "https://discord.gg/8kcHdg2Hch"
GITHUB = "https://github.com/Annoximeme/TrueCombat-Platinum"
FEED = GITHUB + "/releases.atom"

MAPLIST = ["delta", "northport", "railhouse", "snow", "stadtrand", "village"]
PAGES = ["index", "maps", "weapons", "media", "guide", "servers", "leaderboards", "player", "competitive", "news", "devlog", "press", "studio"]

LABELS = {
    "en": {
        "maps": "Maps", "weapons": "Weapons", "guide": "Guide", "servers": "Servers",
        "leaderboards": "Leaderboards", "competitive": "Competitive", "news": "News", "devlog": "Devlog", "press": "Press kit", "media": "Media", "studio": "Studio",
        "gallery": "Gallery", "graphics": "Graphics", "faq": "FAQ", "about": "About",
        "download": "Download", "menu": "Menu", "sections": "Sections", "discord": "Join the Discord",
        "other": "Nederlands", "other_short": "NL", "skip": "Skip to content", "footer": "Footer", "releases": "Releases",
        "dev": "TrueCombat: Platinum is developed by RaziC*.", "col_game": "Game", "col_play": "Play", "col_studio": "Studio", "col_community": "Community", "rss": "Patch notes (RSS)",
        "legal1": "TrueCombat: Elite was created by Team Terminator. Wolfenstein: Enemy Territory is by Splash Damage and id Software, published by Activision. TrueCombat: Platinum is a fan project and is not affiliated with or endorsed by them.",
        "legal2": "Engine code is released under the GPL. Original game data and artwork keep their original terms; see the licenses folder in each download.",
    },
    "nl": {
        "maps": "Maps", "weapons": "Wapens", "guide": "Gids", "servers": "Servers",
        "leaderboards": "Ranglijsten", "competitive": "Competitief", "news": "Nieuws", "devlog": "Devlog", "press": "Perskit", "media": "Media", "studio": "Studio",
        "gallery": "Galerij", "graphics": "Graphics", "faq": "Vragen", "about": "Over",
        "download": "Download", "menu": "Menu", "sections": "Onderdelen", "discord": "Word lid van de Discord",
        "other": "English", "other_short": "EN", "skip": "Naar de inhoud", "footer": "Voettekst", "releases": "Releases",
        "dev": "TrueCombat: Platinum wordt ontwikkeld door RaziC*.", "col_game": "Spel", "col_play": "Spelen", "col_studio": "Studio", "col_community": "Community", "rss": "Patchnotes (RSS)",
        "legal1": "TrueCombat: Elite is gemaakt door Team Terminator. Wolfenstein: Enemy Territory is van Splash Damage en id Software, uitgegeven door Activision. TrueCombat: Platinum is een fanproject en is niet aan hen verbonden of door hen goedgekeurd.",
        "legal2": "De enginecode valt onder de GPL. Originele speldata en artwork houden hun oorspronkelijke voorwaarden; zie de map licenses in elke download.",
    },
}

DISCORD_SVG = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M19.6 5.3A17 17 0 0 0 15.4 4l-.5 1.1a15.7 15.7 0 0 0-5.8 0L8.6 4a17 17 0 0 0-4.2 1.3C1.7 9.3 1 13.2 1.3 17a17.2 17.2 0 0 0 5.2 2.6l1.1-1.8c-.6-.2-1.2-.5-1.7-.8l.4-.3a12.2 12.2 0 0 0 10.4 0l.4.3c-.5.3-1.1.6-1.7.8l1.1 1.8a17.1 17.1 0 0 0 5.2-2.6c.4-4.4-.7-8.3-3-11.7ZM8.7 14.7c-1 0-1.9-.9-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1Zm6.6 0c-1 0-1.9-.9-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1Z"/></svg>')
MENU_SVG = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'


def href(page):
    return "./" if page == "index" else page + ".html"


def url(lang, page):
    return SITE + ("nl/" if lang == "nl" else "") + ("" if page == "index" else page + ".html")


def nav(lang, current):
    L = LABELS[lang]
    other = "en" if lang == "nl" else "nl"
    up = "../" if lang == "nl" else ""
    other_href = ("../" if lang == "nl" else "nl/") + ("" if current == "index" else current + ".html")
    if other_href == "":
        other_href = "./"
    home = "./"
    main = ["maps", "weapons", "media", "guide", "servers", "leaderboards", "competitive", "news"]
    active = {"player": "leaderboards", "devlog": "news"}.get(current, current)
    if current.startswith("devlog-"):
        active = "news"
    links = "\n".join(
        '      <li><a href="%s"%s>%s</a></li>' % (href(p), ' aria-current="page"' if p == active else "", L[p])
        for p in main)
    menu = "".join('<a href="%s">%s</a>' % (href(p), L[p]) for p in main)
    menu += '<a href="%s">%s</a>' % (href("studio"), L["studio"])
    menu += '<hr><a href="%s">%s</a><a href="%s#graphics">%s</a><a href="%s#faq">%s</a><a href="%s">%s</a><a href="%s">Discord</a><a href="%s" hreflang="%s" lang="%s">%s</a>' % (
        home + "#gallery", L["gallery"], home, L["graphics"], home, L["faq"], href("press"), L["press"], DISCORD, other_href, other, other, L["other"])
    return f"""<!--nav-->
<a class="skip" href="#top">{L['skip']}</a>
<header class="nav">
  <div class="wrap">
    <a class="nav-brand" href="{home}"><img src="{up}img/team-terminus-64.webp" alt="" width="30" height="30">TrueCombat <b>Platinum</b></a>
    <ul class="nav-links">
{links}
    </ul>
    <details class="menu" id="menu">
      <summary aria-label="{L['menu']}">{MENU_SVG}</summary>
      <nav aria-label="{L['sections']}">
        {menu}
      </nav>
    </details>
    <a class="nav-lang" href="{other_href}" hreflang="{other}" lang="{other}" title="{L['other']}">{L['other_short']}</a>
    <a class="nav-icon" href="{DISCORD}" aria-label="{L['discord']}" title="{L['discord']}">{DISCORD_SVG}</a>
    <a class="btn" href="{home}#download">{L['download']}</a>
  </div>
</header>
<!--/nav-->"""


GITHUB_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5Z"/></svg>'
RSS_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="19" r="2.2"/><path d="M3 10.5v3a7.5 7.5 0 0 1 7.5 7.5h3A10.5 10.5 0 0 0 3 10.5zm0-6v3A13.5 13.5 0 0 1 16.5 21h3A16.5 16.5 0 0 0 3 4.5z"/></svg>'


def footer(lang):
    L = LABELS[lang]
    up = "../" if lang == "nl" else ""
    cols = [
        (L["col_game"], [(href(p), L[p]) for p in ("maps", "weapons", "guide", "media")] + [("./#download", L["download"])]),
        (L["col_play"], [(href(p), L[p]) for p in ("servers", "leaderboards", "competitive")]),
        (L["col_studio"], [(href(p), L[p]) for p in ("news", "devlog", "studio", "press")]),
        (L["col_community"], [(DISCORD, "Discord"), (GITHUB, "GitHub"), (GITHUB + "/releases", L["releases"]), (FEED, L["rss"])]),
    ]
    nav_html = "\n".join(
        '        <div><p class="foot-h">%s</p>%s</div>' % (h, "".join('<a href="%s">%s</a>' % (u, x) for u, x in items))
        for h, items in cols)
    return f"""<!--footer-->
<footer>
  <div class="wrap">
    <div class="foot">
      <div class="foot-brand">
        <img src="{up}img/team-terminus-160.webp" alt="Team Terminus" width="84" height="84" loading="lazy">
        <div class="who">
          <b>Team Terminus</b>
          <span>{L['dev']}</span>
          <div class="foot-social">
            <a href="{DISCORD}" aria-label="Discord" title="Discord">{DISCORD_SVG}</a>
            <a href="{GITHUB}" aria-label="GitHub" title="GitHub">{GITHUB_SVG}</a>
            <a href="{FEED}" aria-label="{L['rss']}" title="{L['rss']}">{RSS_SVG}</a>
          </div>
        </div>
      </div>
      <nav aria-label="{L['footer']}" class="foot-cols">
{nav_html}
      </nav>
    </div>
    <div class="legal">
      <p>{L['legal1']}</p>
      <p>{L['legal2']}</p>
    </div>
  </div>
</footer>
<!--/footer-->"""


FONTS = ["ibm-plex-sans-latin.woff2", "saira-condensed-700-latin.woff2"]


def social(html):
    """twitter:title and twitter:description, copied from the page's og: tags."""
    out = ""
    html = re.sub(r"<!--alt-->.*?<!--/alt-->", "", html, flags=re.S)
    for key in ("title", "description"):
        if 'name="twitter:%s"' % key in html:
            continue
        m = re.search(r'<meta property="og:%s" content="([^"]*)"' % key, html)
        if m:
            out += '<meta name="twitter:%s" content="%s">\n' % (key, m.group(1))
    return out


def crumbs(lang, page, html):
    """BreadcrumbList structured data: Home > page, or Home > Devlog > post."""
    if page in ("index", "player"):
        return ""
    items = [("TrueCombat: Platinum", url(lang, "index"))]
    if page.startswith("devlog-"):
        items.append(("Devlog", url(lang, "devlog")))
        m = re.search(r'<meta property="og:title" content="([^"]*)"', re.sub(r"<!--alt-->.*?<!--/alt-->", "", html, flags=re.S))
        items.append((htmlmod.unescape(m.group(1)) if m else page, url(lang, page)))
    else:
        items.append((LABELS[lang].get(page, page), url(lang, page)))
    data = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(items)]}
    return '<script type="application/ld+json">%s</script>\n' % json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def alt(lang, page, html=""):
    L = LABELS[lang]
    up = "../" if lang == "nl" else ""
    feed = ""
    if page == "devlog" or page.startswith("devlog-"):
        feed = f'<link rel="alternate" type="application/atom+xml" title="{DL[lang]["feed"]}" href="{SITE}{"nl/" if lang == "nl" else ""}devlog.xml">\n'
    return ("<!--alt-->\n"
            + "".join(f'<link rel="preload" href="{up}fonts/{f}" as="font" type="font/woff2" crossorigin>\n' for f in FONTS)
            + social(html) + crumbs(lang, page, html) + feed +
            f'<link rel="alternate" hreflang="en" href="{url("en", page)}">\n'
            f'<link rel="alternate" hreflang="nl" href="{url("nl", page)}">\n'
            f'<link rel="alternate" hreflang="x-default" href="{url("en", page)}">\n'
            f'<link rel="alternate" type="application/atom+xml" title="{L["rss"]}" href="{FEED}">\n'
            "<!--/alt-->")


def put(html, name, block, path):
    pat = re.compile(r"<!--%s-->.*?<!--/%s-->" % (name, name), re.S)
    if not pat.search(html):
        sys.exit(f"{path}: missing <!--{name}--> markers")
    return pat.sub(lambda m: block, html, count=1)


# ---------------------------------------------------------------- weapons
TEAM = {"en": {"specops": "SpecOps", "terror": "Terrorists", "both": "Both teams"},
        "nl": {"specops": "SpecOps", "terror": "Terroristen", "both": "Beide teams"}}
WL = {
    "en": {"damage": "Damage", "rpm": "Fire rate", "mag": "Magazine", "reload": "Reload", "rpm_u": "rpm",
           "pellets": "9 pellets", "shell": "per shell", "primary": "Primary", "secondary": "Secondary",
           "scope": "scope", "suppressed": "Suppressed", "subsonic": "Subsonic", "equipment": "Equipment",
           "modes": {"semi": "Semi", "auto": "Auto", "3-burst": "3-round burst", "2-burst": "2-round burst",
                     "pump": "Pump", "bolt": "Bolt action", "melee": "Melee", "thrown": "Thrown", "placed": "Placed"}},
    "nl": {"damage": "Schade", "rpm": "Vuursnelheid", "mag": "Magazijn", "reload": "Herladen", "rpm_u": "spm",
           "pellets": "9 hagels", "shell": "per patroon", "primary": "Primair", "secondary": "Secundair",
           "scope": "vizier", "suppressed": "Geluiddemper", "subsonic": "Subsonisch", "equipment": "Uitrusting",
           "modes": {"semi": "Semi", "auto": "Automatisch", "3-burst": "3-schots burst", "2-burst": "2-schots burst",
                     "pump": "Pomp", "bolt": "Grendel", "melee": "Melee", "thrown": "Werpen", "placed": "Plaatsen"}},
}


def weapons_html(lang):
    data = json.loads((HERE / "weapons.json").read_text(encoding="utf-8"))
    W, T = WL[lang], TEAM[lang]
    out = []
    for group in data["groups"]:
        cards = []
        for w in group["weapons"]:
            tags = ['<span class="t-%s">%s</span>' % (w["team"], T[w["team"]])]
            if w.get("slot"):
                tags.append("<span>%s</span>" % W[w["slot"]])
            if w.get("caliber"):
                tags.append("<span>%s</span>" % htmlmod.escape(w["caliber"].replace("12 gauge", "kaliber 12") if lang == "nl" else w["caliber"]))
            if w.get("scope"):
                tags.append("<span>%s %s</span>" % (w["scope"], W["scope"]))
            if w.get("suppressed"):
                tags.append("<span>%s</span>" % W["suppressed"])
            if w.get("subsonic"):
                tags.append("<span>%s</span>" % W["subsonic"])
            modes = "".join("<span>%s</span>" % W["modes"][m] for m in w["modes"])
            if "damage" in w:
                rpm = round(60000 / w["cycle"])
                dmg_label = str(w["damage"]) + ("*" if w.get("pellets") else "")
                reload_s = "%.1f s" % (w["reload"] / 1000)
                if w.get("shell"):
                    reload_s = "%.2f s*" % (w["reload"] / 1000)
                stats = (
                    '<dl class="wstats">'
                    f'<div><dt>{W["damage"]}</dt><span class="bar"><i style="width:{min(100, w["damage"] / 1.5):.0f}%"></i></span><dd>{dmg_label}</dd></div>'
                    f'<div><dt>{W["rpm"]}</dt><span class="bar"><i style="width:{min(100, rpm / 12):.0f}%"></i></span><dd>{rpm} {W["rpm_u"]}</dd></div>'
                    f'<div><dt>{W["mag"]}</dt><span class="bar"><i style="width:{min(100, w["clip"] / 0.3):.0f}%"></i></span><dd>{w["clip"]} / {w["reserve"]}</dd></div>'
                    f'<div><dt>{W["reload"]}</dt><span class="bar"><i style="width:{min(100, w["reload"] / 27):.0f}%"></i></span><dd>{reload_s}</dd></div>'
                    "</dl>")
                note = ""
                if w.get("pellets"):
                    note = '<p class="wnote">* %s</p>' % (
                        "150 damage spread over 9 pellets; reloads one shell at a time." if lang == "en"
                        else "150 schade verdeeld over 9 hagels; laadt patroon voor patroon.")
                cls = "wcard"
                cmp = htmlmod.escape(json.dumps({"dmg": w["damage"], "pel": w.get("pellets", 0), "rpm": rpm, "mag": w["clip"],
                                                 "res": w["reserve"], "rl": w["reload"], "shell": bool(w.get("shell"))}, separators=(",", ":")), quote=True)
            else:
                stats = '<p>%s</p>' % w["note_" + lang]
                note = ""
                cls = "wcard equip"
                cmp = ""
            cards.append(
                f'<article class="{cls}" data-team="{w["team"]}"' + (f" data-w=\"{cmp}\"" if cmp else "") + f'><header><h3>{htmlmod.escape(w.get("name_" + lang, w["name"]))}</h3><span class="full">{htmlmod.escape(w.get("full_" + lang, w["full"]))}</span></header>'
                f'<div class="wtags">{"".join(tags)}</div>{stats}{note}<div class="wmodes">{modes}</div></article>')
        out.append(
            f'<section class="wgroup" id="{group["id"]}"><header><h2>{group["title_" + lang]}</h2><p>{group["sub_" + lang]}</p></header>'
            f'<div class="wgrid">\n' + "\n".join(cards) + "\n</div></section>")
    return "<!--weapons-->\n" + "\n".join(out) + "\n<!--/weapons-->"


# ---------------------------------------------------------------- roadmap
ROAD = {"en": ("Playable now", "Next", "After that"), "nl": ("Nu speelbaar", "Hierna", "Daarna")}


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:2])


def roadmap_html(lang, latest):
    """latest is the newest published release, e.g. 'v0.29.0' (release_sync.py writes it into index.html)."""
    items = json.loads((HERE / "roadmap.json").read_text(encoding="utf-8"))["items"]
    cur = vkey(latest)
    done = [i for i in items if i["version"] and vkey(i["version"]) <= cur]
    future = sorted({i["version"] for i in items if i["version"] and vkey(i["version"]) > cur}, key=vkey)
    nxt = future[0] if future else None
    nxt_items = [i for i in items if nxt and i["version"] == nxt]
    later = [i for i in items if i not in done and i not in nxt_items]
    done = done[-8:]
    h = ROAD[lang]

    def col(cls, title, small, rows):
        lis = "\n".join("          <li>%s</li>" % htmlmod.escape(r[lang]) for r in rows)
        return ('      <div class="road-col %s">\n        <h3>%s%s</h3>\n        <ul>\n%s\n        </ul>\n      </div>'
                % (cls, title, small, lis))
    cols = [col("done", h[0], " <small data-version>%s</small>" % latest, done)]
    if nxt_items:
        cols.append(col("next", h[1], " <small>v%s</small>" % nxt, nxt_items))
    if later:
        cols.append(col("later", h[2], "", later))
    return "<!--roadmap-->\n    <div class=\"road\">\n" + "\n".join(cols) + "\n    </div>\n<!--/roadmap-->"




# ---------------------------------------------------------------- map layouts
LO = {
    "en": {"title": "Layout", "intro": "Top-down plan built from the original map file, with the spawns, bomb sites and flags the game uses and its own location names.",
           "bomb": "Bomb", "flag": "Flag Capture", "callouts": "Location names", "show": "Show",
           "terrorists": "Terrorist spawn", "specops": "SpecOps spawn", "flag_terrorists": "Terrorist flag", "flag_specops": "SpecOps flag",
           "site": "Bomb site", "alt": "Overhead layout of {m}", "nocallouts": "This map has no in-game location names."},
    "nl": {"title": "Plattegrond", "intro": "Bovenaanzicht op basis van het originele mapbestand, met de spawns, bomplekken en vlaggen die het spel gebruikt en de eigen locatienamen.",
           "bomb": "Bomb", "flag": "Flag Capture", "callouts": "Locatienamen", "show": "Tonen",
           "terrorists": "Spawn Terroristen", "specops": "Spawn SpecOps", "flag_terrorists": "Vlag Terroristen", "flag_specops": "Vlag SpecOps",
           "site": "Bomplek", "alt": "Bovenaanzicht van {m}", "nocallouts": "Deze map heeft geen locatienamen in het spel."},
}


def clusters(points, gap):
    """Groups points closer than gap (single link); returns the groups, largest first."""
    left, groups = list(points), []
    while left:
        g = [left.pop()]
        i = 0
        while i < len(g):
            near = [p for p in left if (p[0] - g[i][0]) ** 2 + (p[1] - g[i][1]) ** 2 < gap * gap]
            for p in near:
                left.remove(p)
            g += near
            i += 1
        groups.append(g)
    return sorted(groups, key=len, reverse=True)


def layout_html(lang, name):
    T = LO[lang]
    d = json.loads((HERE / "maplayouts.json").read_text(encoding="utf-8"))[name]
    w, h = d["w"], d["h"]
    u = max(w, h) / 100
    e = lambda s: htmlmod.escape(s)
    svg = []
    for team in ("terrorists", "specops"):
        pts = d["spawns"][team]
        svg.append('<g class="lo-spawn %s">%s' % (team, "".join('<circle cx="%s" cy="%s" r="%.1f"/>' % (x, y, u * .42) for x, y in pts)))
        if pts:
            g = clusters(pts, u * 9)[0]
            cx, cy = sum(p[0] for p in g) / len(g), sum(p[1] for p in g) / len(g)
            cy = cy - u * 2.4 if cy > h * .12 else cy + u * 3.2
            svg.append('<text x="%.1f" y="%.1f" font-size="%.1f" text-anchor="middle">%s</text>' % (cx, cy, u * 1.7, T[team]))
        svg.append("</g>")
    svg.append('<g class="lo-mode lo-bomb">')
    for s in d["sites"]:
        (x1, y1), (x2, y2) = s["a"], s["b"]
        cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
        svg.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f"/>' % (x1, y1, x2 - x1, y2 - y1, u * .4))
        svg.append('<circle class="badge" cx="%.1f" cy="%.1f" r="%.1f"/><text class="letter" x="%.1f" y="%.1f" font-size="%.1f" text-anchor="middle">%s</text>'
                   % (cx, cy, u * 2.1, cx, cy + u * .95, u * 2.7, e(s["site"])))
        label = s["name"] or T["site"]
        svg.append('<text x="%.1f" y="%.1f" font-size="%.1f" text-anchor="middle">%s</text>' % (cx, cy + u * 4.4, u * 1.6, e(label)))
    svg.append('</g><g class="lo-mode lo-flag">')
    for f in d["flags"]:
        x, y = f["p"]
        svg.append('<g class="%s"><circle cx="%s" cy="%s" r="%.1f"/><path d="M%.1f %.1fv-%.1fl%.1f %.1fl-%.1f %.1f"/><text x="%.1f" y="%.1f" font-size="%.1f" text-anchor="middle">%s</text></g>'
                   % (f["team"], x, y, u * 1.5, x - u * .45, y + u * .8, u * 1.7, u * 1.3, u * .55, u * 1.3, u * .55, x, y + u * 3.6, u * 1.6, T["flag_" + f["team"]]))
    svg.append('</g><g class="lo-call">')
    for c in d["callouts"]:
        x, y = c["p"]
        svg.append('<text x="%s" y="%s" font-size="%.1f" text-anchor="middle">%s</text>' % (x, y, u * 1.45, e(c["name"])))
    svg.append("</g>")
    label = name.capitalize()
    call_btn = ('<button type="button" class="lo-toggle" data-lo-call aria-pressed="true">%s</button>' % T["callouts"]) if d["callouts"] else ""
    note = "" if d["callouts"] else '<p class="note">%s</p>' % T["nocallouts"]
    return f"""<!--layout-{name}-->
    <div class="layout" data-layout data-mode="bomb">
      <div class="layout-copy">
        <h3>{T['title']}</h3>
        <p>{T['intro']}</p>
        <div class="lo-controls" role="group" aria-label="{T['show']}">
          <div class="seg"><button type="button" data-lo-mode="bomb" aria-pressed="true">{T['bomb']}</button><button type="button" data-lo-mode="flag" aria-pressed="false">{T['flag']}</button></div>
          {call_btn}
        </div>
        <ul class="lo-legend">
          <li><span class="k t"></span>{T['terrorists']}</li>
          <li><span class="k s"></span>{T['specops']}</li>
        </ul>
        {note}
      </div>
      <figure class="layout-fig" style="--ar: {w} / {h}">
        <img src="img/maps/layout-{name}.webp" alt="{T['alt'].replace('{m}', label)}" width="{w}" height="{h}" loading="lazy">
        <svg viewBox="0 0 {w} {h}" aria-hidden="true">{''.join(svg)}</svg>
      </figure>
    </div>
<!--/layout-{name}-->"""

# ---------------------------------------------------------------- devlog
# A post is tools/website/devlog/<slug>.en.md plus <slug>.nl.md, see the
# README there. An optional "version" in the front matter ties a post to a
# release: until that release is the newest one on the site the post is
# marked "next update, in testing", and the next build after the release
# turns that into "shipped in vX.Y.Z" by itself.
DL = {
    "en": {"read": "Read the post", "feed": "TrueCombat: Platinum devlog", "back": "All devlog posts", "by": "Team Terminus", "more": "More from the devlog",
           "months": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), "min": "{n} min read", "toc": "In this post",
           "shipped": "Shipped in v{v}", "testing": "Next update · in testing", "all": "All posts", "filter": "Filter posts by topic",
           "older": "Older post", "newer": "Newer post", "ask": "Questions about this post? Ask the team on Discord.",
           "discord": "Discuss on Discord", "copy": "Copy link", "copied": "Link copied", "drag": "comparison divider position", "latest": "Latest"},
    "nl": {"read": "Lees het artikel", "feed": "TrueCombat: Platinum devlog", "back": "Alle devlogartikelen", "by": "Team Terminus", "more": "Meer uit de devlog",
           "months": "jan feb mrt apr mei jun jul aug sep okt nov dec".split(), "min": "{n} min lezen", "toc": "In dit artikel",
           "shipped": "Uitgebracht in v{v}", "testing": "Volgende update · in test", "all": "Alle artikelen", "filter": "Filter artikelen op onderwerp",
           "older": "Vorig artikel", "newer": "Volgend artikel", "ask": "Vragen over dit artikel? Stel ze aan het team op Discord.",
           "discord": "Bespreek op Discord", "copy": "Link kopiëren", "copied": "Link gekopieerd", "drag": "positie van de vergelijkingslijn", "latest": "Nieuwste"},
}
DISCORD = "https://discord.gg/8kcHdg2Hch"
LATEST = None  # newest released version on the site, read from index.html


def latest_version():
    global LATEST
    if LATEST is None:
        m = re.search(r"data-version>v([\d.]+)<", (DOCS / "index.html").read_text(encoding="utf-8"))
        LATEST = m.group(1) if m else "0.0.0"
    return LATEST


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def inline(s):
    s = htmlmod.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def anchor(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def markdown(text, lang="en"):
    """The small Markdown subset the devlog uses: ## and ### headings,
    paragraphs, - and 1. lists, > callouts, **bold**, *italic*, `code`,
    [links](url), images and before/after sliders:
        ![Alt text](img/devlog/x.webp "Caption")
        !compare(img/a.webp | Before label | img/b.webp | After label | Caption)
    Returns the HTML and the list of (id, title) for every ## heading."""
    out, toc = [], []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = block.strip().splitlines()
        first = lines[0]
        if first.startswith("### "):
            out.append("<h3>%s</h3>" % inline(first[4:]))
        elif first.startswith("## "):
            hid = anchor(first[3:])
            toc.append((hid, first[3:]))
            out.append('<h2 id="%s">%s</h2>' % (hid, inline(first[3:])))
        elif all(l.startswith("- ") for l in lines):
            out.append("<ul>\n" + "\n".join("  <li>%s</li>" % inline(l[2:]) for l in lines) + "\n</ul>")
        elif all(re.match(r"\d+\. ", l) for l in lines):
            out.append("<ol>\n" + "\n".join("  <li>%s</li>" % inline(l.split(". ", 1)[1]) for l in lines) + "\n</ol>")
        elif all(l.startswith(">") for l in lines):
            body = " ".join(l[1:].strip() for l in lines)
            out.append('<aside class="callout"><p>%s</p></aside>' % inline(body))
        elif len(lines) == 1 and first.startswith("!compare("):
            a, la, b, lb, cap = [x.strip() for x in first[len("!compare("):-1].split("|")]
            out.append(f"""<figure class="wide">
  <div class="compare" data-compare style="--pos:50%; aspect-ratio: 16 / 9">
    <img src="{b}" alt="{htmlmod.escape(lb)}: {htmlmod.escape(cap)}" width="1280" height="720" loading="lazy">
    <img class="top" src="{a}" alt="{htmlmod.escape(la)}: {htmlmod.escape(cap)}" width="1280" height="720" loading="lazy">
    <span class="tag l">{htmlmod.escape(la)}</span>
    <span class="tag r">{htmlmod.escape(lb)}</span>
    <span class="handle"></span>
    <input type="range" min="0" max="100" value="50" aria-label="{htmlmod.escape(cap)}: {DL[lang]['drag']}">
  </div>
  <figcaption>{inline(cap)}</figcaption>
</figure>""")
        elif len(lines) == 1 and re.fullmatch(r'!\[[^\]]*\]\([^)\s]+(?: "[^"]*")?\)', first):
            m = re.fullmatch(r'!\[([^\]]*)\]\(([^)\s]+)(?: "([^"]*)")?\)', first)
            cap = f"\n  <figcaption>{inline(m.group(3))}</figcaption>" if m.group(3) else ""
            out.append(f'<figure class="wide">\n  <img src="{m.group(2)}" alt="{htmlmod.escape(m.group(1))}" width="1280" height="720" loading="lazy">{cap}\n</figure>')
        else:
            out.append("<p>%s</p>" % inline(" ".join(l.strip() for l in lines)))
    return "\n".join(out), toc


def devlog_posts(lang):
    posts = []
    for p in sorted((HERE / "devlog").glob("*.%s.md" % lang)):
        raw = p.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---\n(.*)", raw, re.S)
        if not m:
            sys.exit(f"{p}: missing front matter")
        meta = dict(l.split(": ", 1) for l in m.group(1).splitlines())
        for key in ("title", "date", "summary", "image", "tag"):
            if key not in meta:
                sys.exit(f"{p}: front matter needs '{key}'")
        if not (DOCS / meta["image"]).exists() or not (DOCS / meta["image"].replace(".webp", "-640.webp")).exists():
            sys.exit(f"{p}: {meta['image']} and its -640 version must both exist in docs/")
        meta["slug"] = p.name.split(".")[0]
        meta["body"] = m.group(2)
        words = len(re.findall(r"\w+", meta["body"]))
        meta["minutes"] = max(1, round(words / 220))
        for img in re.findall(r"(?:\]\(|!compare\(|\| )(img/[^)\s|]+)", meta["body"]):
            if not (DOCS / img).exists():
                sys.exit(f"{p}: image {img} not found in docs/")
        posts.append(meta)
    return sorted(posts, key=lambda x: (x["date"], x["slug"]), reverse=True)


def nice_date(lang, iso):
    y, mo, d = iso.split("-")
    return "%d %s %s" % (int(d), DL[lang]["months"][int(mo) - 1], y)


def status_chip(lang, p):
    v = p.get("version")
    if not v:
        return ""
    if vkey(v) <= vkey(latest_version()):
        return f'<span class="state shipped">{DL[lang]["shipped"].format(v=v)}</span>'
    return f'<span class="state testing">{DL[lang]["testing"]}</span>'


def post_meta(lang, p, by=False):
    T = DL[lang]
    extra = f"<span>{T['by']}</span>" if by else ""
    return (f'<p class="post-meta"><span class="tag">{htmlmod.escape(p["tag"])}</span>{status_chip(lang, p)}'
            f'<time datetime="{p["date"]}">{nice_date(lang, p["date"])}</time><span>{T["min"].format(n=p["minutes"])}</span>{extra}</p>')


def post_cards(lang, posts, feature=False):
    T = DL[lang]
    cards = []
    for i, p in enumerate(posts):
        big = feature and i == 0
        art = p["image"] if big else p["image"].replace(".webp", "-640.webp")
        size = 'width="1280" height="720"' if big else 'width="640" height="360"'
        cards.append(f"""      <article class="post-card{' featured' if big else ''}" data-tag="{htmlmod.escape(p['tag'])}">
        <a class="post-art" href="devlog-{p['slug']}.html" tabindex="-1" aria-hidden="true"><img src="{art}" alt="" {size} loading="{'eager' if big else 'lazy'}"></a>
        <div>
          {post_meta(lang, p)}
          <h2><a href="devlog-{p['slug']}.html">{htmlmod.escape(p['title'])}</a></h2>
          <p>{htmlmod.escape(p['summary'])}</p>
          <a class="more" href="devlog-{p['slug']}.html">{T['read']}</a>
        </div>
      </article>""")
    return "\n".join(cards)


def devlog_list(lang, posts):
    return "<!--devlog-->\n" + post_cards(lang, posts, feature=True) + "\n<!--/devlog-->"


def devlog_tags(lang, posts):
    """Topic filter above the post list. Hidden until site.js wires it up."""
    T = DL[lang]
    counts = {}
    for p in posts:
        counts[p["tag"]] = counts.get(p["tag"], 0) + 1
    btns = [f'<button type="button" data-tag="" aria-pressed="true">{T["all"]} <small>{len(posts)}</small></button>']
    for tag in sorted(counts):
        btns.append(f'<button type="button" data-tag="{htmlmod.escape(tag)}" aria-pressed="false">{htmlmod.escape(tag)} <small>{counts[tag]}</small></button>')
    return (f'<!--devlog-tags-->\n    <div class="post-filter" data-post-filter role="group" aria-label="{T["filter"]}" hidden>\n      '
            + "\n      ".join(btns) + "\n    </div>\n<!--/devlog-tags-->")


def devlog_latest(lang, posts):
    p = posts[0]
    return f"""<!--devlog-latest-->
    <a class="promo-card" href="devlog-{p['slug']}.html">
      <img src="{p['image'].replace('.webp', '-640.webp')}" alt="" width="640" height="360" loading="lazy">
      <div>
        <span class="eyebrow">Devlog · <time datetime="{p['date']}">{nice_date(lang, p['date'])}</time>{(' · ' + DL[lang]['testing'].split(' · ')[0]) if 'testing' in status_chip(lang, p) else ''}</span>
        <h3>{htmlmod.escape(p['title'])}</h3>
        <p>{htmlmod.escape(p['summary'])}</p>
        <span class="more">{DL[lang]['read']}</span>
      </div>
    </a>
<!--/devlog-latest-->"""


def devlog_feed(lang, posts):
    base = SITE + ("nl/" if lang == "nl" else "")
    esc = lambda s: htmlmod.escape(s, quote=False)
    entries = "".join(f"""  <entry>
    <title>{esc(p['title'])}</title>
    <link href="{base}devlog-{p['slug']}.html"/>
    <id>{base}devlog-{p['slug']}.html</id>
    <published>{p['date']}T12:00:00Z</published>
    <updated>{p.get('updated', p['date'])}T12:00:00Z</updated>
    <category term="{htmlmod.escape(p['tag'])}"/>
    <summary>{esc(p['summary'])}</summary>
    <author><name>Team Terminus</name></author>
  </entry>
""" for p in posts)
    newest = max(p.get("updated", p["date"]) for p in posts)
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="{lang}">
  <title>{DL[lang]['feed']}</title>
  <link href="{base}devlog.html"/>
  <link rel="self" href="{base}devlog.xml"/>
  <id>{base}devlog.html</id>
  <updated>{newest}T12:00:00Z</updated>
{entries}</feed>
"""


def devlog_page(lang, post, posts, template):
    """A full post page, built from the head of devlog.html."""
    T = DL[lang]
    page = "devlog-" + post["slug"]
    head = template[:template.index("<!--nav-->")]
    title = htmlmod.escape(post["title"])
    desc = htmlmod.escape(post["summary"], quote=True)
    head = re.sub(r"<title>.*?</title>", f"<title>{title} · TrueCombat: Platinum</title>", head)
    head = re.sub(r'(<meta (?:name|property)="(?:description|og:description)" content=")[^"]*"', lambda m: m.group(1) + desc + '"', head)
    head = re.sub(r'(<meta property="og:title" content=")[^"]*"', lambda m: m.group(1) + title + '"', head)
    head = head.replace('content="website"', 'content="article"')
    ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": post["title"], "description": post["summary"],
          "datePublished": post["date"], "dateModified": post.get("updated", post["date"]), "inLanguage": lang,
          "articleSection": post["tag"], "timeRequired": "PT%dM" % post["minutes"],
          "image": SITE + "img/og-devlog-%s.jpg" % post["slug"], "mainEntityOfPage": url(lang, page),
          "author": {"@type": "Organization", "name": "Team Terminus", "url": SITE + "studio.html"},
          "publisher": {"@type": "Organization", "name": "Team Terminus", "logo": {"@type": "ImageObject", "url": SITE + "img/team-terminus.webp"}}}
    head = head.replace("<!--alt-->", '<meta property="article:published_time" content="%s">\n<meta property="article:section" content="%s">\n<script type="application/ld+json">%s</script>\n<!--alt-->'
                        % (post["date"], htmlmod.escape(post["tag"]), json.dumps(ld, ensure_ascii=False, separators=(",", ":"))), 1)
    head = head.replace(url("en", "devlog"), url(lang, page))
    head = head.replace("img/og-devlog.jpg", "img/og-%s.jpg" % page)
    if lang == "nl":
        head = head.replace('<html lang="en">', '<html lang="nl">', 1).replace('content="en_GB"', 'content="nl_NL"')

    body_html, toc = markdown(post["body"], lang)
    toc_html = ""
    if len(toc) >= 3:
        toc_html = (f'\n      <nav class="post-toc" aria-label="{T["toc"]}">\n        <span class="eyebrow">{T["toc"]}</span>\n        <ol>\n'
                    + "\n".join(f'          <li><a href="#{hid}">{inline(t)}</a></li>' for hid, t in toc)
                    + "\n        </ol>\n      </nav>")

    i = [p["slug"] for p in posts].index(post["slug"])
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i + 1 < len(posts) else None
    def step(p, label, cls):
        if not p:
            return '<span></span>'
        return f'<a class="{cls}" href="devlog-{p["slug"]}.html"><small>{label}</small>{htmlmod.escape(p["title"])}</a>'
    pager = f"""
      <nav class="post-pager">
        {step(older, T['older'], 'prev')}
        {step(newer, T['newer'], 'next')}
      </nav>"""

    # related: same topic first, then the newest others
    others = [p for p in posts if p["slug"] != post["slug"]]
    others = sorted(others, key=lambda p: p["tag"] != post["tag"])[:2]
    more = ""
    if others:
        more = f"""
<section class="band">
  <div class="wrap">
    <div class="section-head"><span class="eyebrow">{T['more']}</span></div>
    <div class="post-list">
{post_cards(lang, others)}
    </div>
  </div>
</section>
"""
    body = f"""<!--nav-->
<!--/nav-->

<main id="top">
<article class="post">
  <header class="page-head post-head">
    <div class="head-art" style="--art: url({post['image']}); --art-s: url({post['image'].replace('.webp', '-640.webp')})" aria-hidden="true"></div>
    <div class="wrap">
      <a class="back" href="devlog.html">{T['back']}</a>
      {post_meta(lang, post, by=True)}
      <h1>{title}</h1>
      <p class="lede">{htmlmod.escape(post['summary'])}</p>
    </div>
  </header>
  <div class="band">
    <div class="wrap post-body">{toc_html}
      <div class="prose">
{body_html}
      </div>
      <div class="post-end">
        <p>{T['ask']}</p>
        <div class="news-tools">
          <a class="btn btn-ghost" href="{DISCORD}">{T['discord']}</a>
          <button type="button" class="btn btn-ghost" data-copy-link data-done="{T['copied']}">{T['copy']}</button>
        </div>
      </div>{pager}
    </div>
  </div>
</article>
{more}</main>

<!--footer-->
<!--/footer-->

<script src="js/site.js"></script>
</body>
</html>
"""
    html = head + body
    if lang == "nl":
        html = ASSET.sub(r"../\1/", html).replace('href="style.css"', 'href="../style.css"')
    html = put(html, "nav", nav(lang, page), page)
    html = put(html, "footer", footer(lang), page)
    html = put(html, "alt", alt(lang, page, html), page)
    return html


# ---------------------------------------------------------------- Dutch
ASSET = re.compile(r"(?<=[\s\"'(,])(img|js|press)/")


def to_dutch(page, html):
    sys.path.insert(0, str(HERE))
    import nl  # noqa: E402
    pairs = nl.COMMON + nl.PAGES.get(page, [])
    missing = []
    for en, du in pairs:
        if en not in html:
            if (en, du) in nl.COMMON:
                continue
            missing.append(en)
            continue
        html = html.replace(en, du)
    if missing:
        sys.exit("nl.py: %s.html no longer contains:\n  " % page + "\n  ".join(m[:90] for m in missing))
    html = html.replace('<html lang="en">', '<html lang="nl">', 1)
    months = dict(zip("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), "jan feb mrt apr mei jun jul aug sep okt nov dec".split()))
    html = re.sub(r"\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})\b", lambda m: "%s %s %s" % (m.group(1), months[m.group(2)], m.group(3)), html)
    html = ASSET.sub(r"../\1/", html)
    html = html.replace('href="style.css"', 'href="../style.css"')
    html = html.replace('content="' + url("en", page) + '"', 'content="' + url("nl", page) + '"')
    html = html.replace('rel="canonical" href="' + url("en", page) + '"', 'rel="canonical" href="' + url("nl", page) + '"')
    html = html.replace('<meta property="og:locale" content="en_GB">', '<meta property="og:locale" content="nl_NL">')
    return html


def lastmod(path):
    """The date a page last changed: today when it differs from the last commit, else that commit's date."""
    import datetime
    import subprocess
    today = datetime.date.today().isoformat()
    try:
        rel = str(path.relative_to(ROOT))
        if subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT).returncode:
            return today
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out or today
    except (OSError, ValueError):
        return today


def main():
    (DOCS / "nl").mkdir(exist_ok=True)
    for page in PAGES:
        path = DOCS / (page + ".html")
        en = path.read_text(encoding="utf-8")
        if page == "weapons":
            en = put(en, "weapons", weapons_html("en"), path)
        if page == "index":
            m = re.search(r"data-version>(v[\d.]+)<", en)
            latest = m.group(1) if m else "v0.0.0"
            en = put(en, "roadmap", roadmap_html("en", latest), path)
            en = put(en, "devlog-latest", devlog_latest("en", devlog_posts("en")), path)
        if page == "devlog":
            en = put(en, "devlog", devlog_list("en", devlog_posts("en")), path)
            en = put(en, "devlog-tags", devlog_tags("en", devlog_posts("en")), path)
        if page == "maps":
            for name in MAPLIST:
                en = put(en, "layout-" + name, layout_html("en", name), path)
        src = en
        en = put(en, "nav", nav("en", page), path)
        en = put(en, "footer", footer("en"), path)
        en = put(en, "alt", alt("en", page, en), path)
        path.write_text(en, encoding="utf-8")

        du = src
        if page == "index":
            du = put(du, "roadmap", roadmap_html("nl", latest), path)
            du = put(du, "devlog-latest", devlog_latest("nl", devlog_posts("nl")), path)
        if page == "weapons":
            du = put(du, "weapons", weapons_html("nl"), path)
        if page == "devlog":
            du = put(du, "devlog", devlog_list("nl", devlog_posts("nl")), path)
            du = put(du, "devlog-tags", devlog_tags("nl", devlog_posts("nl")), path)
        if page == "maps":
            for name in MAPLIST:
                du = put(du, "layout-" + name, layout_html("nl", name), path)
        du = to_dutch(page, du)
        du = put(du, "nav", nav("nl", page), path)
        du = put(du, "footer", footer("nl"), path)
        du = put(du, "alt", alt("nl", page, du), path)
        (DOCS / "nl" / (page + ".html")).write_text(du, encoding="utf-8")

    template = (DOCS / "devlog.html").read_text(encoding="utf-8")
    posts = {lang: devlog_posts(lang) for lang in ("en", "nl")}
    if [p["slug"] for p in posts["en"]] != [p["slug"] for p in posts["nl"]]:
        sys.exit("devlog: every post needs both an .en.md and an .nl.md file")
    for lang in ("en", "nl"):
        for post in posts[lang]:
            out = DOCS / ("nl" if lang == "nl" else "") / ("devlog-%s.html" % post["slug"])
            out.write_text(devlog_page(lang, post, posts[lang], template), encoding="utf-8")

    for lang in ("en", "nl"):
        (DOCS / ("nl" if lang == "nl" else "") / "devlog.xml").write_text(devlog_feed(lang, posts[lang]), encoding="utf-8")

    rows = []
    # player.html without an id is an empty profile, so only real pages go in the sitemap
    for page in [p for p in PAGES if p != "player"] + ["devlog-" + p["slug"] for p in posts["en"]]:
        for lang in ("en", "nl"):
            alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l, url(l, page)) for l in ("en", "nl"))
            rows.append("  <url><loc>%s</loc><lastmod>%s</lastmod>%s</url>" % (url(lang, page), lastmod(DOCS / ("nl" if lang == "nl" else "") / (page + ".html")), alts))
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")
    print("built %d pages in English and Dutch" % len(PAGES))


if __name__ == "__main__":
    main()
