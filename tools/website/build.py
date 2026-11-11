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
  5. writes the download, FAQ and TrueCombat: Elite pages in full from landing.py,
  6. writes the site search index (docs/js/search-<lang>.json) and docs/llms.txt,
  7. writes docs/sitemap.xml, with the screenshots on each page.

Run it after changing any English page:   python tools/website/build.py
"""
import html as htmlmod
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import landing  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
HERE = pathlib.Path(__file__).resolve().parent
SITE = "https://truecombat.eu/"
DISCORD = "https://discord.gg/8kcHdg2Hch"
GITHUB = "https://github.com/Annoximeme/TrueCombat-Platinum"
FEED = GITHUB + "/releases.atom"

MAPLIST = ["delta", "northport", "railhouse", "snow", "stadtrand", "village"]
# written out in full by this script from landing.py (the other pages are hand-edited)
LANDING = ["download", "faq", "truecombat-elite"]
PAGES = ["index", "maps", "weapons", "media", "guide", "servers", "leaderboards", "player", "competitive", "news", "devlog", "press", "studio", "support"]

LABELS = {
    "en": {
        "maps": "Maps", "weapons": "Weapons", "guide": "Guide", "servers": "Servers",
        "leaderboards": "Leaderboards", "competitive": "Competitive", "news": "News", "devlog": "Devlog", "press": "Press kit", "media": "Media", "studio": "Studio", "support": "Support",
        "gallery": "Gallery", "graphics": "Graphics", "faq": "FAQ", "about": "About", "truecombat-elite": "TrueCombat: Elite", "search": "Search", "top": "Back to top",
        "download": "Download", "menu": "Menu", "sections": "Sections", "discord": "Join the Discord",
        "other": "Nederlands", "other_short": "NL", "skip": "Skip to content", "footer": "Footer", "releases": "Releases",
        "dev": "TrueCombat: Platinum is developed by RaziC*.", "col_game": "Game", "col_play": "Play", "col_studio": "Studio", "col_community": "Community", "rss": "Patch notes (RSS)",
        "legal1": "TrueCombat: Elite was created by Team Terminator. Wolfenstein: Enemy Territory is by Splash Damage and id Software, published by Activision. TrueCombat: Platinum is a fan project and is not affiliated with or endorsed by them.",
        "legal2": "Engine code is released under the GPL. Original game data and artwork keep their original terms; see the licenses folder in each download.",
    },
    "nl": {
        "maps": "Maps", "weapons": "Wapens", "guide": "Gids", "servers": "Servers",
        "leaderboards": "Ranglijsten", "competitive": "Competitief", "news": "Nieuws", "devlog": "Devlog", "press": "Perskit", "media": "Media", "studio": "Studio", "support": "Steun ons",
        "gallery": "Galerij", "graphics": "Graphics", "faq": "Vragen", "about": "Over", "truecombat-elite": "TrueCombat: Elite", "search": "Zoeken", "top": "Terug naar boven",
        "download": "Download", "menu": "Menu", "sections": "Onderdelen", "discord": "Word lid van de Discord",
        "other": "English", "other_short": "EN", "skip": "Naar de inhoud", "footer": "Voettekst", "releases": "Releases",
        "dev": "TrueCombat: Platinum wordt ontwikkeld door RaziC*.", "col_game": "Spel", "col_play": "Spelen", "col_studio": "Studio", "col_community": "Community", "rss": "Patchnotes (RSS)",
        "legal1": "TrueCombat: Elite is gemaakt door Team Terminator. Wolfenstein: Enemy Territory is van Splash Damage en id Software, uitgegeven door Activision. TrueCombat: Platinum is een fanproject en is niet aan hen verbonden of door hen goedgekeurd.",
        "legal2": "De enginecode valt onder de GPL. Originele speldata en artwork houden hun oorspronkelijke voorwaarden; zie de map licenses in elke download.",
    },
}

DISCORD_SVG = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M19.6 5.3A17 17 0 0 0 15.4 4l-.5 1.1a15.7 15.7 0 0 0-5.8 0L8.6 4a17 17 0 0 0-4.2 1.3C1.7 9.3 1 13.2 1.3 17a17.2 17.2 0 0 0 5.2 2.6l1.1-1.8c-.6-.2-1.2-.5-1.7-.8l.4-.3a12.2 12.2 0 0 0 10.4 0l.4.3c-.5.3-1.1.6-1.7.8l1.1 1.8a17.1 17.1 0 0 0 5.2-2.6c.4-4.4-.7-8.3-3-11.7ZM8.7 14.7c-1 0-1.9-.9-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1Zm6.6 0c-1 0-1.9-.9-1.9-2.1s.8-2.1 1.9-2.1 1.9 1 1.9 2.1-.8 2.1-1.9 2.1Z"/></svg>')
HEART_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21s-7.5-4.6-10-9.3C.4 8.6 2.1 4.5 6 4.1c2.2-.2 4.1 1 6 3.2 1.9-2.2 3.8-3.4 6-3.2 3.9.4 5.6 4.5 4 7.6C19.5 16.4 12 21 12 21z"/></svg>'
SEARCH_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.6-3.6"/></svg>'
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
    menu += '<a href="%s">%s</a><a href="%s">%s</a>' % (href("studio"), L["studio"], href("support"), L["support"])
    menu += '<hr><a href="%s">%s</a><a href="%s#graphics">%s</a><a href="%s">%s</a><a href="%s">%s</a><a href="%s">Discord</a><a href="%s" hreflang="%s" lang="%s">%s</a>' % (
        home + "#gallery", L["gallery"], home, L["graphics"], href("faq"), L["faq"], href("press"), L["press"], DISCORD, other_href, other, other, L["other"])
    menu = menu.replace('<hr>', '<hr><a href="%s">%s</a><a href="%s">%s</a>' % (href("download"), L["download"], href("truecombat-elite"), L["truecombat-elite"]), 1)
    download = home + "#download" if current == "index" else href("download")
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
        <button type="button" class="menu-search" data-search-open>{SEARCH_SVG}{L['search']}</button>{menu}
      </nav>
    </details>
    <button class="nav-search" type="button" data-search-open aria-label="{L['search']}" title="{L['search']} (Ctrl K)">{SEARCH_SVG}</button>
    <a class="nav-lang" href="{other_href}" hreflang="{other}" lang="{other}" title="{L['other']}">{L['other_short']}</a>
    <a class="nav-support" href="{href('support')}"{' aria-current="page"' if current == 'support' else ''} title="{L['support']}">{HEART_SVG}<span>{L['support']}</span></a>
    <a class="nav-icon" href="{DISCORD}" aria-label="{L['discord']}" title="{L['discord']}">{DISCORD_SVG}</a>
    <a class="btn" href="{download}">{L['download']}</a>
  </div>
</header>
<!--/nav-->"""


GITHUB_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5Z"/></svg>'
RSS_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="19" r="2.2"/><path d="M3 10.5v3a7.5 7.5 0 0 1 7.5 7.5h3A10.5 10.5 0 0 0 3 10.5zm0-6v3A13.5 13.5 0 0 1 16.5 21h3A16.5 16.5 0 0 0 3 4.5z"/></svg>'


def footer(lang):
    L = LABELS[lang]
    up = "../" if lang == "nl" else ""
    cols = [
        (L["col_game"], [(href(p), L[p]) for p in ("download", "maps", "weapons", "guide", "media", "faq", "truecombat-elite")]),
        (L["col_play"], [(href(p), L[p]) for p in ("servers", "leaderboards", "competitive")]),
        (L["col_studio"], [(href(p), L[p]) for p in ("news", "devlog", "studio", "press", "support")]),
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


# Instant navigation: Chromium fetches a same-site page the moment a link is hovered or pressed, so the
# click itself is served from memory. It is a prefetch, not a prerender: no script runs early, so devlog
# read counts and the live server polls stay honest. Other browsers ignore the block.
SPECULATION = ('<script type="speculationrules">{"prefetch":[{"where":{"and":[{"href_matches":"/*"},'
               '{"not":{"href_matches":"/press/*"}},{"not":{"href_matches":"/devlog-stats*"}},'
               '{"not":{"selector_matches":"[download],[target=_blank]"}}]},"eagerness":"moderate"}]}</script>\n')

SHOTS = ["map-northport", "map-railhouse", "map-delta", "map-stadtrand", "map-village", "map-snow", "hud-scoreboard", "media-deployment"]
GAME_DESC = {
    "en": "A free, native 64-bit DirectX 12 rebuild of TrueCombat: Elite, the realistic tactical shooter, for Windows 10 and 11.",
    "nl": "Een gratis, native 64-bit DirectX 12-versie van TrueCombat: Elite, de realistische tactische shooter, voor Windows 10 en 11.",
}


def ld(data):
    return '<script type="application/ld+json">%s</script>\n' % json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def org_ld():
    return {"@type": "Organization", "@id": SITE + "#studio", "name": "Team Terminus", "url": SITE + "studio.html",
            "logo": {"@type": "ImageObject", "url": SITE + "img/team-terminus.webp"}, "sameAs": [GITHUB, DISCORD, "https://ko-fi.com/truecombatplatinum"]}


def game_node(lang):
    return {"@type": "VideoGame", "@id": SITE + "#game", "name": "TrueCombat: Platinum", "alternateName": ["TC:P", "TrueCombat Platinum"],
            "url": url(lang, "index"), "image": SITE + "img/og.jpg", "description": GAME_DESC[lang], "inLanguage": ["en", "nl"],
            "genre": ["Tactical shooter", "First-person shooter"], "gamePlatform": "PC", "operatingSystem": "Windows 10, Windows 11 (64-bit)",
            "applicationCategory": "Game", "playMode": "MultiPlayer", "softwareVersion": latest_version(),
            "isBasedOn": {"@type": "VideoGame", "name": "TrueCombat: Elite"},
            "screenshot": [SITE + "img/%s.webp" % n for n in SHOTS],
            "author": {"@id": SITE + "#studio"}, "publisher": {"@id": SITE + "#studio"},
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR", "availability": "https://schema.org/InStock", "url": url(lang, "download")},
            "downloadUrl": url(lang, "download"), "installUrl": url(lang, "download"),
            "sameAs": [GITHUB, DISCORD]}


def game_ld(lang):
    """Home page structured data: the site, the studio and the game, as one linked graph."""
    site = {"@type": "WebSite", "@id": SITE + "#site", "url": SITE, "name": "TrueCombat: Platinum", "alternateName": "truecombat.eu",
            "inLanguage": ["en", "nl"], "publisher": {"@id": SITE + "#studio"}}
    return ld({"@context": "https://schema.org", "@graph": [site, org_ld(), game_node(lang)]})


def alt(lang, page, html=""):
    L = LABELS[lang]
    up = "../" if lang == "nl" else ""
    feed = ""
    if page == "devlog" or page.startswith("devlog-"):
        feed = f'<link rel="alternate" type="application/atom+xml" title="{DL[lang]["feed"]}" href="{SITE}{"nl/" if lang == "nl" else ""}devlog.xml">\n'
    return ("<!--alt-->\n"
            + "".join(f'<link rel="preload" href="{up}fonts/{f}" as="font" type="font/woff2" crossorigin>\n' for f in FONTS)
            + f'<link rel="apple-touch-icon" href="{up}img/apple-touch-icon.png">\n'
            + f'<link rel="manifest" href="{up}site.webmanifest">\n'
            + SPECULATION
            + social(html) + (game_ld(lang) if page == "index" else "") + crumbs(lang, page, html) + feed +
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
    used = set()
    for group in data["groups"]:
        cards = []
        for w in group["weapons"]:
            wid = re.sub(r"[^a-z0-9]+", "-", w["name"].lower()).strip("-")
            if wid in used:
                wid += "-" + w["team"]
            used.add(wid)
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
                f'<article class="{cls}" id="{wid}" data-team="{w["team"]}"' + (f" data-w=\"{cmp}\"" if cmp else "") + f'><header><h3>{htmlmod.escape(w.get("name_" + lang, w["name"]))}</h3><span class="full">{htmlmod.escape(w.get("full_" + lang, w["full"]))}</span></header>'
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
           "discord": "Discuss on Discord", "copy": "Copy link", "copied": "Link copied", "drag": "comparison divider position", "latest": "Latest",
           "rateQ": "Was this worth the read?", "rateGroup": "Rate this post", "star": "1 star", "stars": "{n} stars",
           "rateThanks": "Thanks for rating. You can change your rating until the end of the day.", "rateFail": "Your rating could not be sent. Please try again later.",
           "ratePriv": "Anonymous. No account, no cookies."},
    "nl": {"read": "Lees het artikel", "feed": "TrueCombat: Platinum devlog", "back": "Alle devlogartikelen", "by": "Team Terminus", "more": "Meer uit de devlog",
           "months": "jan feb mrt apr mei jun jul aug sep okt nov dec".split(), "min": "{n} min lezen", "toc": "In dit artikel",
           "shipped": "Uitgebracht in v{v}", "testing": "Volgende update · in test", "all": "Alle artikelen", "filter": "Filter artikelen op onderwerp",
           "older": "Vorig artikel", "newer": "Volgend artikel", "ask": "Vragen over dit artikel? Stel ze aan het team op Discord.",
           "discord": "Bespreek op Discord", "copy": "Link kopiëren", "copied": "Link gekopieerd", "drag": "positie van de vergelijkingslijn", "latest": "Nieuwste",
           "rateQ": "Was dit artikel de moeite waard?", "rateGroup": "Beoordeel dit artikel", "star": "1 ster", "stars": "{n} sterren",
           "rateThanks": "Bedankt voor je beoordeling. Je kunt ze tot het einde van de dag nog aanpassen.", "rateFail": "Je beoordeling kon niet worden verzonden. Probeer het later opnieuw.",
           "ratePriv": "Anoniem. Geen account, geen cookies."},
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
    # "time: HH:MM" (optional) orders posts published on the same day
    return sorted(posts, key=lambda x: (x["date"], x.get("time", "00:00"), x["slug"]), reverse=True)


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
            f'<time datetime="{p["date"]}">{nice_date(lang, p["date"])}</time><span>{T["min"].format(n=p["minutes"])}</span>{extra}'
            f'<span class="post-stat" data-post-stat="{p["slug"]}" hidden></span></p>')


def post_cards(lang, posts, feature=False, h="h2"):
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
          <{h}><a href="devlog-{p['slug']}.html">{htmlmod.escape(p['title'])}</a></{h}>
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
    RATE_STARS = "\n          ".join(f'<button type="button" role="radio" aria-checked="false" data-stars="{n}" aria-label="{T["star"] if n == 1 else T["stars"].format(n=n)}"></button>' for n in range(1, 6))
    body = f"""<!--nav-->
<!--/nav-->

<main id="top">
<article class="post" data-post="{post['slug']}" data-min="{post['minutes']}">
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
      <div class="post-rate" data-rate="{post['slug']}" data-thanks="{T['rateThanks']}" data-fail="{T['rateFail']}" hidden>
        <p class="rate-q" id="rate-q">{T['rateQ']}</p>
        <div class="rate-stars" role="radiogroup" aria-labelledby="rate-q">
          {RATE_STARS}
        </div>
        <p class="rate-note" aria-live="polite">{T['ratePriv']}</p>
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


# ---------------------------------------------------------------- studio
SR = {"en": {"latest": "Latest", "items": "{n} additions", "item": "1 addition"}, "nl": {"latest": "Nieuwste", "items": "{n} toevoegingen", "item": "1 toevoeging"}}


def studio_releases(lang, latest):
    """Release-by-release history on the studio page, from roadmap.json. Grows by itself with every release."""
    items = json.loads((HERE / "roadmap.json").read_text(encoding="utf-8"))["items"]
    cur = vkey(latest)
    vers = sorted({i["version"] for i in items if i["version"] and vkey(i["version"]) <= cur}, key=vkey, reverse=True)
    rows = []
    for n, v in enumerate(vers):
        its = [i for i in items if i["version"] == v]
        lis = "".join("<li>%s</li>" % htmlmod.escape(i[lang]) for i in its)
        tag = ' <span class="latest">%s</span>' % SR[lang]["latest"] if n == 0 else ""
        rows.append('      <li class="rel%s"><div class="rel-ver"><b>v%s</b>%s<small>%s</small></div><ul>%s</ul></li>'
                    % (" now" if n == 0 else "", v, tag, (SR[lang]["item"] if len(its) == 1 else SR[lang]["items"].format(n=len(its))), lis))
    return "<!--studio-releases-->\n    <ol class=\"releases-line\">\n" + "\n".join(rows) + "\n    </ol>\n<!--/studio-releases-->"


WS = {"en": {"testing": "In testing", "dev": "In development", "next": "Next update"},
      "nl": {"testing": "In de test", "dev": "In ontwikkeling", "next": "Volgende update"}}
WS_SKIP = ("Anti-Cheat",)  # not announced on the studio page yet


def studio_workshop(lang, latest):
    """What the team is working on now, from roadmap.json: the next version's items, then unscheduled plans."""
    items = json.loads((HERE / "roadmap.json").read_text(encoding="utf-8"))["items"]
    items = [i for i in items if not any(k in i["en"] for k in WS_SKIP)]
    cur = vkey(latest)
    future = sorted({i["version"] for i in items if i["version"] and vkey(i["version"]) > cur}, key=vkey)
    nxt = future[0] if future else None
    testing = [(i, "testing") for i in items if nxt and i["version"] == nxt]
    dev = [(i, "dev") for i in items if not i["version"]]
    rows = testing[:4] + dev[:4]
    rows += (testing[4:] + dev[4:])[:8 - len(rows)]
    T = WS[lang]
    lis = "\n".join('      <li class="ws-%s"><span class="ws-state">%s</span><b>%s</b></li>' % (st, T[st], htmlmod.escape(i[lang])) for i, st in rows)
    return "<!--studio-workshop-->\n    <ul class=\"workshop\">\n" + lis + "\n    </ul>\n<!--/studio-workshop-->"


def studio_devlog(lang, posts):
    return "<!--studio-devlog-->\n    <div class=\"post-list post-trio\">\n" + post_cards(lang, posts[:3], h="h3") + "\n    </div>\n<!--/studio-devlog-->"



# ---------------------------------------------------------------- support / transparency
MONTHS = {"en": "January February March April May June July August September October November December".split(),
          "nl": "januari februari maart april mei juni juli augustus september oktober november december".split()}
FUND_T = {
    "en": {"eyebrow": "Where the money goes", "h2": "Every euro, accounted for",
           "lede": "Running TrueCombat: Platinum costs about <b>&euro;%d a month</b>. That is also our monthly goal on Ko-fi. This is exactly what it covers.",
           "order_h": "In this order", "order": ["Running costs come first: servers, infrastructure and the domain.", "Then a reserve of three months of running costs, so the servers stay up through a quiet month.", "Only then development time and tools."],
           "report_h": "Monthly report", "report_lede": "Every contribution is counted live as it comes in. After every month we add what went out and what is left in reserve.",
           "first": "The first report is published in %s.", "month": "Month", "in": "Received", "out": "Spent", "reserve": "Reserve",
           "goal": "Monthly goal"},
    "nl": {"eyebrow": "Waar het geld naartoe gaat", "h2": "Elke euro verantwoord",
           "lede": "TrueCombat: Platinum draaiende houden kost ongeveer <b>&euro;%d per maand</b>. Dat is ook ons maanddoel op Ko-fi. Dit is precies wat het dekt.",
           "order_h": "In deze volgorde", "order": ["Eerst de vaste kosten: servers, infrastructuur en het domein.", "Dan een reserve van drie maanden vaste kosten, zodat de servers ook in een rustige maand online blijven.", "Pas daarna ontwikkeltijd en tools."],
           "report_h": "Maandverslag", "report_lede": "Elke bijdrage wordt live geteld zodra ze binnenkomt. Na elke maand vullen we aan wat er uitging en wat er in reserve blijft.",
           "first": "Het eerste verslag verschijnt %s.", "month": "Maand", "in": "Ontvangen", "out": "Uitgegeven", "reserve": "Reserve",
           "goal": "Maanddoel"},
}


def eur(n):
    s = "&euro;{:,}".format(abs(int(round(n)))).replace(",", ".")
    return ("&minus;" + s) if n < 0 else s


def support_funding(lang):
    import html as H
    d = json.loads((HERE / "funding.json").read_text(encoding="utf-8"))
    T = FUND_T[lang]
    covers = "\n".join('      <li><h3>%s</h3><p>%s</p></li>' % (H.escape(c[lang][0]), H.escape(c[lang][1])) for c in d["covers"])
    order = "".join("<li>%s</li>" % o for o in T["order"])
    if d["months"]:
        rows, reserve = [], 0
        for m in d["months"]:
            y, mo = m["month"].split("-")
            reserve += m["received"] - m["spent"]
            rows.append("<tr><td>%s %s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (MONTHS[lang][int(mo) - 1].capitalize(), y, eur(m["received"]), eur(m["spent"]), eur(reserve)))
        report = ('<div class="table-scroll"><table class="fund-table"><thead><tr><th>%s</th><th>%s</th><th>%s</th><th>%s</th></tr></thead><tbody>%s</tbody></table></div>'
                  % (T["month"], T["in"], T["out"], T["reserve"], "".join(reversed(rows))))
    else:
        report = '<p class="fund-empty">%s</p>' % (T["first"] % d["first_report"][lang])
    report = '<div class="fund-report" data-fund=\'%s\' data-goal="%d">%s</div>' % (
        json.dumps({m["month"]: m["spent"] for m in d["months"]}), d["goal"], report)
    return f"""<!--support-funding-->
<section class="band band-alt" id="where">
  <div class="wrap">
    <div class="section-head">
      <span class="eyebrow">{T['eyebrow']}</span>
      <h2>{T['h2']}</h2>
      <p class="lede">{T['lede'] % d['goal']}</p>
    </div>
    <div class="fund-goal"><span>{T['goal']}</span><b>{eur(d['goal'])}</b></div>
    <ul class="fund-covers">
{covers}
    </ul>
    <div class="fund-split">
      <div><h3>{T['order_h']}</h3><ol class="fund-order">{order}</ol></div>
      <div><h3>{T['report_h']}</h3><p>{T['report_lede']}</p>{report}</div>
    </div>
  </div>
</section>
<!--/support-funding-->"""


# ---------------------------------------------------------------- landing pages
OGLOCALE = {"en": "en_GB", "nl": "nl_NL"}


def release_values():
    """Version, size, date and link of the current download, as the release workflow wrote them on the home page."""
    home = (DOCS / "index.html").read_text(encoding="utf-8")
    def grab(pat, default):
        m = re.search(pat, home)
        return m.group(1) if m else default
    return {"version": grab(r"data-version>(v[\d.]+)<", "v0.0.0"), "size": grab(r"<span data-size>([^<]*)<", ""),
            "date": grab(r"<span data-date>([^<]*)<", ""), "link": grab(r'<a [^>]*data-download[^>]*href="([^"]*)"', GITHUB + "/releases/latest"),
            "is_setup": 'data-kind="short">Installer<' in home}


def strip_tags(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s))


def landing_page(lang, page):
    up = "../" if lang == "nl" else ""
    v = release_values()
    kind = {"en": ("Windows installer", "Full game, zip"), "nl": ("Windows-installatieprogramma", "Volledig spel, zip")}[lang][0 if v["is_setup"] else 1]
    date = v["date"]
    if lang == "nl":
        months = dict(zip("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), "jan feb mrt apr mei jun jul aug sep okt nov dec".split()))
        date = re.sub(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b", lambda m: months[m.group(1)], date)
    values = {"up": up, "version": v["version"], "size": v["size"], "date": date, "link": v["link"], "kind": kind}
    title, desc, og = landing.meta(page, lang)
    e = lambda t: htmlmod.escape(t, quote=True)
    extra = ""
    if page == "faq":
        extra = ld({"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": lang, "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a.replace('href="', 'href="' + url(lang, "index")).replace(url(lang, "index") + "http", "http").replace(url(lang, "index") + "./", url(lang, "index"))}}
            for _, q, a in landing.faq_items(lang)]})
    if page == "download":
        node = game_node(lang)
        node.pop("@id")
        node.update({"@context": "https://schema.org", "@type": ["VideoGame", "SoftwareApplication"], "downloadUrl": v["link"],
                     "author": {"@type": "Organization", "name": "Team Terminus", "url": SITE + "studio.html"}})
        node.pop("publisher")
        extra = ld(node)
    if page == "truecombat-elite":
        extra = ld({"@context": "https://schema.org", "@type": "Article", "headline": strip_tags(landing.ELITE_T[lang]["h1"]), "description": desc,
                    "inLanguage": lang, "image": SITE + "img/og-truecombat-elite.jpg", "mainEntityOfPage": url(lang, page),
                    "about": [{"@type": "VideoGame", "name": "TrueCombat: Elite"}, {"@type": "VideoGame", "name": "TrueCombat: Platinum", "url": SITE}],
                    "author": {"@type": "Organization", "name": "Team Terminus", "url": SITE + "studio.html"},
                    "publisher": {"@type": "Organization", "name": "Team Terminus", "logo": {"@type": "ImageObject", "url": SITE + "img/team-terminus.webp"}}})
    html = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#0d1016">
<link rel="canonical" href="{url(lang, page)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url(lang, page)}">
<meta property="og:site_name" content="TrueCombat: Platinum">
<meta property="og:locale" content="{OGLOCALE[lang]}">
<meta property="og:title" content="{e(title.split(' · TrueCombat: Platinum')[0])}">
<meta property="og:description" content="{e(og)}">
<meta property="og:image" content="{SITE}img/og-{page}.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}img/og-{page}.jpg">
{extra}<!--alt-->
<!--/alt-->
<link rel="icon" type="image/png" href="{up}img/favicon.png">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<!--nav-->
<!--/nav-->

<main id="top">
{landing.body(page, lang, values)}</main>

<!--footer-->
<!--/footer-->

<script src="{up}js/site.js"></script>
</body>
</html>
"""
    html = put(html, "nav", nav(lang, page), page)
    html = put(html, "footer", footer(lang), page)
    html = put(html, "alt", alt(lang, page, html), page)
    return html


# ---------------------------------------------------------------- site search
KIND = {"en": {"page": "Page", "section": "Section", "weapon": "Weapon", "map": "Map", "post": "Devlog", "faq": "Question", "release": "Patch notes"},
        "nl": {"page": "Pagina", "section": "Onderdeel", "weapon": "Wapen", "map": "Map", "post": "Devlog", "faq": "Vraag", "release": "Patchnotes"}}


def search_index(lang, posts):
    """Everything the Ctrl+K search can find: pages, their sections, weapons, maps, devlog posts, FAQ entries and releases."""
    K = KIND[lang]
    base = DOCS / ("nl" if lang == "nl" else "")
    rows = []
    def text(s):
        return re.sub(r"\s+", " ", strip_tags(s)).strip()
    for page in [p for p in PAGES if p != "player"] + LANDING:
        html = (base / (page + ".html")).read_text(encoding="utf-8")
        title = text(re.search(r"<title>(.*?)</title>", html, re.S).group(1)).split(" · ")[0]
        if page == "index":
            title = "TrueCombat: Platinum"
        desc = htmlmod.unescape(re.search(r'<meta name="description" content="([^"]*)"', html).group(1))
        rows.append({"t": title, "u": href(page), "k": K["page"], "d": desc})
        main = html[html.index("<main"):html.index("</main>")]
        if page == "news":
            for m in re.finditer(r'<details class="release" id="([^"]+)".*?<span class="sum">(.*?)</span>', main, re.S):
                rows.append({"t": m.group(1), "u": "news.html#" + m.group(1), "k": K["release"], "d": text(m.group(2))[:150]})
            continue
        if page == "faq":
            for qid, q, a in landing.faq_items(lang):
                rows.append({"t": text(q), "u": "faq.html#" + qid, "k": K["faq"], "d": text(a)[:150]})
            continue
        for m in re.finditer(r'<section[^>]*\bid="([^"]+)"[^>]*>', main):
            h = re.search(r"<h([23])[^>]*>(.*?)</h\1>", main[m.end():m.end() + 1800], re.S)
            if not h:
                continue
            kind = K["map"] if page == "maps" and m.group(1) in MAPLIST else K["section"]
            rows.append({"t": text(h.group(2)), "u": href(page) + "#" + m.group(1), "k": kind, "d": LABELS[lang].get(page, title) if page != "index" else ""})
    weapons = (base / "weapons.html").read_text(encoding="utf-8")
    for m in re.finditer(r'<article class="[^"]*" id="([^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3><span class="full">(.*?)</span>', weapons, re.S):
        rows.append({"t": text(m.group(2)), "u": "weapons.html#" + m.group(1), "k": K["weapon"], "d": text(m.group(3))})
    for p in posts:
        rows.append({"t": p["title"], "u": "devlog-%s.html" % p["slug"], "k": K["post"], "d": p["summary"][:150]})
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":"))


def llms_txt(posts):
    """A plain-text summary of the site for AI assistants and answer engines (llmstxt.org)."""
    v = release_values()
    def line(page, note):
        return "- [%s](%s): %s" % (LABELS["en"].get(page, page).replace("FAQ", "Questions and answers"), url("en", page), note)
    out = ["# TrueCombat: Platinum", "",
           "> TrueCombat: Platinum is a free, native 64-bit Windows rebuild of TrueCombat: Elite (TC:E), the realistic modern-combat tactical shooter "
           "originally made as a total conversion for Wolfenstein: Enemy Territory. It has a DirectX 12 renderer with an OpenGL fallback, the original maps, "
           "weapons, movement and HUD, a launcher with signed updates, official EU servers and leaderboards. It is developed by Team Terminus.", "",
           "- Current version: %s (%s)" % (v["version"], v["date"]),
           "- Platform: Windows 10 and 11, 64-bit. Price: free. Status: early access.",
           "- Not affiliated with Team Terminator, the creators of TrueCombat: Elite. Fan project.",
           "- The site is also available in Dutch under %snl/." % SITE, "",
           "## Start here", "",
           line("download", "the installer, system requirements and first steps"),
           line("faq", "install, online play, graphics and project questions"),
           line("truecombat-elite", "what TrueCombat: Elite was and how Platinum compares with the original"),
           line("guide", "controls, movement and stamina, game modes, tactics and hosting"), "",
           "## The game", "",
           line("maps", "the six maps (Delta, Northport, Railhouse, Snow, Stadtrand, Village) with overhead layouts"),
           line("weapons", "all 27 guns with their damage, recoil and handling values"),
           line("media", "in-game screenshots from the DirectX 12 renderer"),
           line("competitive", "match mode for clan matches: ready-up, knife round, half-time, timeouts"), "",
           "## Play", "",
           line("servers", "public and official servers, live scoreboards and latest results"),
           line("leaderboards", "ranks and ratings from every ranked match"), "",
           "## Studio", "",
           line("news", "patch notes for every release"),
           line("devlog", "articles on how the game is built"),
           line("studio", "Team Terminus, the people behind the game"),
           line("press", "press kit with logos, screenshots and a fact sheet"),
           line("support", "how the project is funded and where the money goes"), "",
           "## Devlog", ""]
    out += ["- [%s](%s): %s" % (p["title"], url("en", "devlog-" + p["slug"]), p["summary"]) for p in posts]
    return "\n".join(out) + "\n"


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


# ---------------------------------------------------------------- cache busting
# style.css and site.js get ?v=<content hash>, so a deploy never pairs new HTML with a cached old
# stylesheet or script. Sources are read back without the suffix, so the rest of the build is unchanged.
VERSIONED = re.compile(r'((?:href|src)="(?:\.\./)?(?:style\.css|js/site\.js))\?v=[0-9a-f]+"')


def unbust(html):
    return VERSIONED.sub(r'\1"', html)


def bust(html):
    import hashlib
    for name, attr in (("style.css", "href"), ("js/site.js", "src")):
        v = hashlib.sha1((DOCS / name).read_bytes()).hexdigest()[:10]
        html = re.sub(r'(%s="(?:\.\./)?%s)"' % (attr, re.escape(name)), r'\1?v=%s"' % v, html)
    return html


OLD_LASTMOD = {}


def page_images(path):
    """Game screenshots on a page, for the image sitemap."""
    html = path.read_text(encoding="utf-8")
    html = html[html.index("<main"):html.index("</main>")] if "<main" in html else html
    seen = []
    for m in re.finditer(r'(?:src|data-src)="(?:\.\./)?(img/[^"]+\.webp)"|url\((?:\.\./)?(img/[^)]+\.webp)\)', html):
        name = m.group(1) or m.group(2)
        if "-640" in name or "team-" in name or "logo" in name or name in seen:
            continue
        seen.append(name)
    return seen[:24]


def lastmod(path):
    """The date a page last changed: today when it differs from the last commit, else that commit's date."""
    import datetime
    import subprocess
    today = datetime.date.today().isoformat()
    try:
        rel = str(path.relative_to(ROOT))
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel], cwd=ROOT, capture_output=True).returncode == 0
        if not tracked or subprocess.run(["git", "diff", "--quiet", "HEAD", "--", rel], cwd=ROOT).returncode:
            return today
        # a shallow clone only knows its newest commit, which would stamp every page with the same date
        if subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=ROOT, capture_output=True, text=True).stdout.strip() == "true":
            old = OLD_LASTMOD.get(SITE + str(path.relative_to(DOCS)).replace("\\", "/").replace("index.html", ""))
            if old:
                return old
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out or today
    except (OSError, ValueError):
        return today


def main():
    (DOCS / "nl").mkdir(exist_ok=True)
    for page in PAGES:
        path = DOCS / (page + ".html")
        en = unbust(path.read_text(encoding="utf-8"))
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
        if page == "studio":
            en = put(en, "studio-releases", studio_releases("en", "v" + latest_version()), path)
            en = put(en, "studio-devlog", studio_devlog("en", devlog_posts("en")), path)
            en = put(en, "studio-workshop", studio_workshop("en", "v" + latest_version()), path)
        if page == "support":
            en = put(en, "support-funding", support_funding("en"), path)
        src = en
        en = put(en, "nav", nav("en", page), path)
        en = put(en, "footer", footer("en"), path)
        en = put(en, "alt", alt("en", page, en), path)
        path.write_text(bust(en), encoding="utf-8")

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
        if page == "studio":
            du = put(du, "studio-releases", studio_releases("nl", "v" + latest_version()), path)
            du = put(du, "studio-devlog", studio_devlog("nl", devlog_posts("nl")), path)
            du = put(du, "studio-workshop", studio_workshop("nl", "v" + latest_version()), path)
        if page == "support":
            du = put(du, "support-funding", support_funding("nl"), path)
        du = to_dutch(page, du)
        du = put(du, "nav", nav("nl", page), path)
        du = put(du, "footer", footer("nl"), path)
        du = put(du, "alt", alt("nl", page, du), path)
        (DOCS / "nl" / (page + ".html")).write_text(bust(du), encoding="utf-8")

    for page in LANDING:
        for lang in ("en", "nl"):
            (DOCS / ("nl" if lang == "nl" else "") / (page + ".html")).write_text(bust(landing_page(lang, page)), encoding="utf-8")

    template = unbust((DOCS / "devlog.html").read_text(encoding="utf-8"))
    posts = {lang: devlog_posts(lang) for lang in ("en", "nl")}
    if [p["slug"] for p in posts["en"]] != [p["slug"] for p in posts["nl"]]:
        sys.exit("devlog: every post needs both an .en.md and an .nl.md file")
    for lang in ("en", "nl"):
        for post in posts[lang]:
            out = DOCS / ("nl" if lang == "nl" else "") / ("devlog-%s.html" % post["slug"])
            out.write_text(bust(devlog_page(lang, post, posts[lang], template)), encoding="utf-8")

    for lang in ("en", "nl"):
        (DOCS / ("nl" if lang == "nl" else "") / "devlog.xml").write_text(devlog_feed(lang, posts[lang]), encoding="utf-8")

    for lang in ("en", "nl"):
        (DOCS / "js" / ("search-%s.json" % lang)).write_text(search_index(lang, posts[lang]), encoding="utf-8")
    (DOCS / "llms.txt").write_text(llms_txt(posts["en"]), encoding="utf-8")

    old = DOCS / "sitemap.xml"
    if old.exists():
        OLD_LASTMOD.update(re.findall(r"<url><loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", old.read_text(encoding="utf-8")))
    rows = []
    # player.html without an id is an empty profile, so only real pages go in the sitemap
    for page in [p for p in PAGES if p != "player"] + LANDING + ["devlog-" + p["slug"] for p in posts["en"]]:
        for lang in ("en", "nl"):
            alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l, url(l, page)) for l in ("en", "nl"))
            path = DOCS / ("nl" if lang == "nl" else "") / (page + ".html")
            images = "".join("<image:image><image:loc>%s%s</image:loc></image:image>" % (SITE, i) for i in page_images(path))
            rows.append("  <url><loc>%s</loc><lastmod>%s</lastmod>%s%s</url>" % (url(lang, page), lastmod(path), alts, images))
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")
    print("built %d pages in English and Dutch" % (len(PAGES) + len(LANDING)))


if __name__ == "__main__":
    main()
