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
import detail  # noqa: E402
import i18n  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
HERE = pathlib.Path(__file__).resolve().parent
SITE = "https://truecombat.eu/"
DISCORD = "https://discord.gg/8kcHdg2Hch"
GITHUB = "https://github.com/Annoximeme/TrueCombat-Platinum"
FEED = GITHUB + "/releases.atom"

MAPLIST = ["delta", "northport", "railhouse", "snow", "stadtrand", "village"]
# written out in full by this script from landing.py (the other pages are hand-edited)
LANDING = ["download", "faq", "truecombat-elite", "privacy"]
PAGES = ["index", "maps", "weapons", "media", "guide", "servers", "leaderboards", "player", "competitive", "news", "devlog", "press", "studio", "support"]

LABELS = {
    "en": {
        "maps": "Maps", "weapons": "Weapons", "guide": "Guide", "servers": "Servers",
        "leaderboards": "Leaderboards", "competitive": "Competitive", "news": "News", "devlog": "Devlog", "press": "Press kit", "media": "Media", "studio": "Studio", "support": "Support", "privacy": "Privacy",
        "gallery": "Gallery", "graphics": "Graphics", "faq": "FAQ", "about": "About", "truecombat-elite": "TrueCombat: Elite", "search": "Search", "top": "Back to top",
        "download": "Download", "menu": "Menu", "sections": "Sections", "discord": "Join the Discord", "language": "Language",
        "other": "Nederlands", "other_short": "NL", "skip": "Skip to content", "footer": "Footer", "releases": "Releases",
        "dev": "TrueCombat: Platinum is developed by RaziC*.", "col_game": "Game", "col_play": "Play", "col_studio": "Studio", "col_community": "Community", "rss": "Patch notes (RSS)",
        "legal1": "TrueCombat: Elite was created by Team Terminator. Wolfenstein: Enemy Territory is by Splash Damage and id Software, published by Activision. TrueCombat: Platinum is a fan project and is not affiliated with or endorsed by them.",
        "legal2": "Engine code is released under the GPL. Original game data and artwork keep their original terms; see the licenses folder in each download.",
    },
    "nl": {
        "maps": "Maps", "weapons": "Wapens", "guide": "Gids", "servers": "Servers",
        "leaderboards": "Ranglijsten", "competitive": "Competitief", "news": "Nieuws", "devlog": "Devlog", "press": "Perskit", "media": "Media", "studio": "Studio", "support": "Steun ons", "privacy": "Privacy",
        "gallery": "Galerij", "graphics": "Graphics", "faq": "Vragen", "about": "Over", "truecombat-elite": "TrueCombat: Elite", "search": "Zoeken", "top": "Terug naar boven",
        "download": "Download", "menu": "Menu", "sections": "Onderdelen", "discord": "Word lid van de Discord", "language": "Taal",
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


XLANGS = i18n.LANGS                  # translated from i18n/<code>.py, with English filling any gap
LANGS = ["en", "nl"] + XLANGS


def sub(lang):
    """The folder a language is published in: none for English."""
    return "" if lang == "en" else lang


def pre(lang):
    return "" if lang == "en" else lang + "/"


def upp(lang):
    return "" if lang == "en" else "../"


def has(lang, page):
    """Whether the page exists in the language. The extra languages leave the devlog and studio pages in English."""
    return lang not in XLANGS or not (page in i18n.EN_ONLY or page.startswith("devlog-"))


def langs_for(page):
    return [l for l in LANGS if has(l, page)]


def url(lang, page):
    if not has(lang, page):
        lang = "en"
    return SITE + pre(lang) + ("" if page == "index" else page + ".html")


def english_links(lang, html):
    """In the extra languages, links to pages that only exist in English lead to the English site."""
    if lang not in XLANGS:
        return html
    return re.sub(r'href="((?:%s)(?:-[^"./]*)?\.(?:html|xml)(?:#[^"]*)?)"' % "|".join(i18n.EN_ONLY), r'href="../\1"', html)


def nav(lang, current):
    L = LABELS[lang]
    up = upp(lang)
    file = "" if current == "index" else current + ".html"
    others = [(l, (up + pre(l) + file) or "./") for l in langs_for(current) if l != lang]
    lang_links = "".join('<a href="%s" hreflang="%s" lang="%s">%s</a>' % (h, l, l, i18n.NAMES[l]) for l, h in others)
    home = "./"
    main = ["maps", "weapons", "media", "guide", "servers", "leaderboards", "competitive", "news", "devlog"]
    active = {"player": "leaderboards", "match": "servers"}.get(current, current)
    if current.startswith("devlog-"):
        active = "devlog"
    if current.startswith("map-"):
        active = "maps"
    if current.startswith("weapon-"):
        active = "weapons"
    links = "\n".join(
        '      <li><a href="%s"%s%s>%s</a></li>' % (href(p), ' aria-current="page"' if p == active else "",
                                               ' data-devlog-new="%s"' % devlog_posts(lang)[0]["date"] if p == "devlog" else "", L[p])
        for p in main)
    menu = "".join('<a href="%s">%s</a>' % (href(p), L[p]) for p in main)
    menu += '<a href="%s">%s</a><a href="%s">%s</a>' % (href("studio"), L["studio"], href("support"), L["support"])
    menu += '<hr><a href="%s">%s</a><a href="%s#graphics">%s</a><a href="%s">%s</a><a href="%s">%s</a><a href="%s">Discord</a><hr>%s' % (
        home + "#gallery", L["gallery"], home, L["graphics"], href("faq"), L["faq"], href("press"), L["press"], DISCORD, lang_links)
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
    <details class="nav-langs"><summary aria-label="{L['language']}" title="{L['language']}">{lang.upper()}</summary><div>{lang_links}</div></details>
    <a class="nav-support" href="{href('support')}"{' aria-current="page"' if current == 'support' else ''} title="{L['support']}">{HEART_SVG}<span>{L['support']}</span></a>
    <a class="nav-icon" href="{DISCORD}" aria-label="{L['discord']}" title="{L['discord']}">{DISCORD_SVG}</a>
    <a class="btn" href="{download}">{L['download']}</a>
  </div>
</header>
<!--/nav-->"""


GITHUB_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.3c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5Z"/></svg>'
RSS_SVG = '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="5" cy="19" r="2.2"/><path d="M3 10.5v3a7.5 7.5 0 0 1 7.5 7.5h3A10.5 10.5 0 0 0 3 10.5zm0-6v3A13.5 13.5 0 0 1 16.5 21h3A16.5 16.5 0 0 0 3 4.5z"/></svg>'


def footer(lang, page=""):
    L = LABELS[lang]
    up = upp(lang)
    cols = [
        (L["col_game"], [(href(p), L[p]) for p in ("download", "maps", "weapons", "guide", "media", "faq", "truecombat-elite")]),
        (L["col_play"], [(href(p), L[p]) for p in ("servers", "leaderboards", "competitive")]),
        (L["col_studio"], [(href(p), L[p]) for p in ("news", "devlog", "studio", "press", "support", "privacy")]),
        (L["col_community"], [(DISCORD, "Discord"), (GITHUB, "GitHub"), (GITHUB + "/releases", L["releases"]), (FEED, L["rss"])]),
    ]
    nav_html = "\n".join(
        '        <div><p class="foot-h">%s</p>%s</div>' % (h, "".join('<a href="%s">%s</a>' % (u, x) for u, x in items))
        for h, items in cols)
    strip = "" if page == "index" or page.startswith("devlog") else devlog_strip(lang)
    return f"""<!--footer-->
{strip}<footer>
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
    if page in ("index", "player", "match"):
        return ""
    items = [("TrueCombat: Platinum", url(lang, "index"))]
    if page.startswith("devlog-"):
        items.append(("Devlog", url(lang, "devlog")))
        m = re.search(r'<meta property="og:title" content="([^"]*)"', re.sub(r"<!--alt-->.*?<!--/alt-->", "", html, flags=re.S))
        items.append((htmlmod.unescape(m.group(1)) if m else page, url(lang, page)))
    elif page.startswith(("map-", "weapon-")):
        parent = "maps" if page.startswith("map-") else "weapons"
        items.append((LABELS[lang][parent], url(lang, parent)))
        m = re.search(r"<h1>(.*?)</h1>", html, re.S)
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
            "url": url(lang, "index"), "image": SITE + "img/og.jpg", "description": GAME_DESC[lang], "inLanguage": LANGS,
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
            "inLanguage": LANGS, "publisher": {"@id": SITE + "#studio"}}
    return ld({"@context": "https://schema.org", "@graph": [site, org_ld(), game_node(lang)]})


def alt(lang, page, html=""):
    L = LABELS[lang]
    up = upp(lang)
    feed = ""
    if page == "devlog" or page.startswith("devlog-"):
        feed = f'<link rel="alternate" type="application/atom+xml" title="{DL[lang]["feed"]}" href="{SITE}{pre(lang)}devlog.xml">\n'
    return ("<!--alt-->\n"
            + "".join(f'<link rel="preload" href="{up}fonts/{f}" as="font" type="font/woff2" crossorigin>\n' for f in FONTS)
            + f'<link rel="apple-touch-icon" href="{up}img/apple-touch-icon.png">\n'
            + f'<link rel="manifest" href="{up}site.webmanifest">\n'
            + SPECULATION
            + social(html) + (game_ld(lang) if page == "index" else "") + crumbs(lang, page, html) + feed +
            "".join(f'<link rel="alternate" hreflang="{l}" href="{url(l, page)}">\n' for l in langs_for(page)) +
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
           "pellets": "9 pellets", "pellet_note": "150 damage spread over 9 pellets; reloads one shell at a time.", "shell": "per shell", "primary": "Primary", "secondary": "Secondary",
           "scope": "scope", "suppressed": "Suppressed", "subsonic": "Subsonic", "equipment": "Equipment",
           "modes": {"semi": "Semi", "auto": "Auto", "3-burst": "3-round burst", "2-burst": "2-round burst",
                     "pump": "Pump", "bolt": "Bolt action", "melee": "Melee", "thrown": "Thrown", "placed": "Placed"}},
    "nl": {"damage": "Schade", "rpm": "Vuursnelheid", "mag": "Magazijn", "reload": "Herladen", "rpm_u": "spm",
           "pellets": "9 hagels", "pellet_note": "150 schade verdeeld over 9 hagels; laadt patroon voor patroon.", "shell": "per patroon", "primary": "Primair", "secondary": "Secundair",
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
        cards, group_note = [], ""
        for w in group["weapons"]:
            wid = re.sub(r"[^a-z0-9]+", "-", w["name"].lower()).strip("-")
            if wid in used:
                wid += "-" + w["team"]
            used.add(wid)
            tags = ['<span class="t-%s">%s</span>' % (w["team"], T[w["team"]])]
            if w.get("slot"):
                tags.append("<span>%s</span>" % W[w["slot"]])
            if w.get("caliber"):
                tags.append("<span>%s</span>" % htmlmod.escape(detail.caliber(lang, w["caliber"])))
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
                    f'<div><dt>{W["damage"]}</dt><dd><span class="bar" aria-hidden="true"><i style="width:{min(100, w["damage"] / 1.5):.0f}%"></i></span><b>{dmg_label}</b></dd></div>'
                    f'<div><dt>{W["rpm"]}</dt><dd><span class="bar" aria-hidden="true"><i style="width:{min(100, rpm / 12):.0f}%"></i></span><b>{rpm} {W["rpm_u"]}</b></dd></div>'
                    f'<div><dt>{W["mag"]}</dt><dd><span class="bar" aria-hidden="true"><i style="width:{min(100, w["clip"] / 0.3):.0f}%"></i></span><b>{w["clip"]} / {w["reserve"]}</b></dd></div>'
                    f'<div><dt>{W["reload"]}</dt><dd><span class="bar" aria-hidden="true"><i style="width:{min(100, w["reload"] / 27):.0f}%"></i></span><b>{reload_s}</b></dd></div>'
                    "</dl>")
                note = ""
                if w.get("pellets"):
                    group_note = '<p class="wnote">* %s</p>' % W["pellet_note"]
                cls = "wcard"
                cmp = htmlmod.escape(json.dumps({"dmg": w["damage"], "pel": w.get("pellets", 0), "rpm": rpm, "mag": w["clip"],
                                                 "res": w["reserve"], "rl": w["reload"], "shell": bool(w.get("shell"))}, separators=(",", ":")), quote=True)
            else:
                stats = '<p>%s</p>' % detail.local(lang, w, "note")
                note = ""
                cls = "wcard equip"
                cmp = ""
            cards.append(
                f'<article class="{cls}" id="{wid}" data-team="{w["team"]}"' + (f" data-w=\"{cmp}\"" if cmp else "") + f'><header><h3><a href="weapon-{wid}.html">{htmlmod.escape(detail.local(lang, w, "name"))}</a></h3><span class="full">{htmlmod.escape(detail.local(lang, w, "full"))}</span></header>'
                f'<div class="wtags">{"".join(tags)}</div>{stats}{note}<div class="wmodes">{modes}</div></article>')
        out.append(
            f'<section class="wgroup" id="{group["id"]}"><header><h2>{detail.local(lang, group, "title")}</h2><p>{detail.local(lang, group, "sub")}</p></header>'
            f'<div class="wgrid">\n' + "\n".join(cards) + "\n</div>" + group_note + "</section>")
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
        lis = "\n".join("          <li>%s</li>" % htmlmod.escape(r[lang] if lang in r else i18n.tx(lang, r["en"])) for r in rows)
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


def layout_html(lang, name, intro=True):
    T = LO[lang]
    intro_p = "<p>%s</p>" % T["intro"] if intro else ""
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
        {intro_p}
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
            out.append('<div class="callout"><p>%s</p></div>' % inline(body))
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
    if lang in XLANGS:
        lang = "en"
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
        small = p["image"].replace(".webp", "-640.webp")
        # the featured card is full width on phones and about 60% wide on desktop: let the browser pick the size
        srcset = (' srcset="%s 640w, %s 1280w" sizes="(max-width: 860px) 100vw, 60vw"' % (small, p["image"])) if big and (DOCS / small).exists() else ""
        cards.append(f"""      <article class="post-card{' featured' if big else ''}" data-tag="{htmlmod.escape(p['tag'])}">
        <a class="post-art" href="devlog-{p['slug']}.html" tabindex="-1" aria-hidden="true"><img src="{art}"{srcset} alt="" {size} loading="{'eager' if big else 'lazy'}"></a>
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
    """The second promo card on the home page. The newest devlog post already leads the "Follow the build"
    section just above, so this card points at the TrueCombat: Elite page instead of repeating the post."""
    T = landing.ELITE_T[lang]
    return f"""<!--devlog-latest-->
    <a class="promo-card" href="truecombat-elite.html">
      <img src="img/player-models-640.webp" alt="" width="640" height="360" loading="lazy">
      <div>
        <span class="eyebrow">{T['c_orig']}</span>
        <h3>{T['h1']}</h3>
        <p>{T['og']}</p>
        <span class="more">{T['n2']}</span>
      </div>
    </a>
<!--/devlog-latest-->"""


DEVREACH = {
    "en": {"new": "New devlog", "eyebrow": "In development", "h2": "Follow the build", "all": "All devlog posts",
           "lede": "TrueCombat: Platinum is built in the open. Every significant piece of work gets an article: what changed, why, and what comes next.",
           "strip": "From the devlog"},
    "nl": {"new": "Nieuwe devlog", "eyebrow": "In ontwikkeling", "h2": "Volg de bouw", "all": "Alle devlogartikelen",
           "lede": "TrueCombat: Platinum wordt in het openbaar gebouwd. Elk belangrijk stuk werk krijgt een artikel: wat er veranderde, waarom, en wat er volgt.",
           "strip": "Uit de devlog"},
}


def devlog_hero(lang, posts):
    """Home page hero: one line that leads to the newest devlog post."""
    p = posts[0]
    return (f'<!--devlog-hero-->\n    <a class="hero-log" href="devlog-{p["slug"]}.html"><b>{DEVREACH[lang]["new"]}</b>'
            f'<span>{htmlmod.escape(p["title"])}</span><time datetime="{p["date"]}">{nice_date(lang, p["date"])}</time></a>\n<!--/devlog-hero-->')


def devlog_home(lang, posts):
    """Home page: the three newest devlog posts, high on the page."""
    T = DEVREACH[lang]
    cards = "\n".join(
        f"""      <a class="log-card{' lead' if i == 0 else ''}" href="devlog-{p['slug']}.html">
        <img src="{p['image'].replace('.webp', '-640.webp')}" alt="" width="640" height="360" loading="lazy">
        <div><span class="eyebrow">{htmlmod.escape(p['tag'])} · <time datetime="{p['date']}">{nice_date(lang, p['date'])}</time></span>
        <h3>{htmlmod.escape(p['title'])}</h3>
        <p>{htmlmod.escape(p['summary'])}</p></div>
      </a>""" for i, p in enumerate(posts[:3]))
    return f"""<!--devlog-home-->
<section class="band band-alt" id="devlog">
  <div class="wrap">
    <div class="section-head head-row">
      <div><span class="eyebrow">{T['eyebrow']}</span><h2>{T['h2']}</h2><p class="lede">{T['lede']}</p></div>
      <div class="hero-cta"><a class="btn btn-ghost" href="devlog.html">{T['all']} ({len(posts)})</a></div>
    </div>
    <div class="log-cards">
{cards}
    </div>
  </div>
</section>
<!--/devlog-home-->"""


def devlog_strip(lang):
    """Above the footer of every page outside the devlog: the two newest posts."""
    T = DEVREACH[lang]
    posts = devlog_posts(lang)[:2]
    links = "".join(f'<a href="devlog-{p["slug"]}.html"><time datetime="{p["date"]}">{nice_date(lang, p["date"])}</time><span>{htmlmod.escape(p["title"])}</span></a>' for p in posts)
    return (f'<aside class="log-strip" aria-label="{T["strip"]}"><div class="wrap"><a class="log-strip-h" href="devlog.html">{T["strip"]}</a>'
            f'<div class="log-strip-posts">{links}</div><a class="log-strip-all" href="devlog.html">{T["all"]}</a></div></aside>\n')


def devlog_feed(lang, posts):
    base = SITE + (pre(lang))
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


def snippet(text, limit=160):
    """A meta description search engines show in full: whole sentences up to the limit, else whole words and an ellipsis."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    ends = [m.end() for m in re.finditer(r"[.!?](?=\s)", text[:limit + 1])]
    if ends and ends[-1] >= limit * 0.55:
        return text[:ends[-1]]
    return text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "\u2026"


def devlog_page(lang, post, posts, template):
    """A full post page, built from the head of devlog.html."""
    T = DL[lang]
    page = "devlog-" + post["slug"]
    head = template[:template.index("<!--nav-->")]
    title = htmlmod.escape(post["title"])
    desc = htmlmod.escape(snippet(post["summary"]), quote=True)
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
    html = put(html, "footer", footer(lang, page), page)
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
    home = unbust((DOCS / "index.html").read_text(encoding="utf-8"))
    def grab(pat, default):
        m = re.search(pat, home)
        return m.group(1) if m else default
    return {"version": grab(r"data-version>(v[\d.]+)<", "v0.0.0"), "size": grab(r"<span data-size>([^<]*)<", ""),
            "date": grab(r"<span data-date>([^<]*)<", ""), "link": grab(r'<a [^>]*data-download[^>]*href="([^"]*)"', GITHUB + "/releases/latest"),
            "is_setup": 'data-kind="short">Installer<' in home}


def strip_tags(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s))


INSTALL_KIND = {"en": {"setup": "Windows installer", "zip": "Full game, zip"}, "nl": {"setup": "Windows-installatieprogramma", "zip": "Volledig spel, zip"}}
SHORT_MONTHS = {"en": {"m": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec"}, "nl": {"m": "jan feb mrt apr mei jun jul aug sep okt nov dec"}}


def short_months(lang, text):
    """Dates written as '9 Nov 2026' in the page source, with the month in the page's language."""
    if lang == "en":
        return text
    months = dict(zip(SHORT_MONTHS["en"]["m"].split(), SHORT_MONTHS[lang]["m"].split()))
    return re.sub(r"\b(\d{1,2}) (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (\d{4})\b", lambda m: "%s %s %s" % (m.group(1), months[m.group(2)], m.group(3)), text)


def landing_page(lang, page):
    up = upp(lang)
    v = release_values()
    kind = INSTALL_KIND[lang]["setup" if v["is_setup"] else "zip"]
    date = short_months(lang, v["date"])
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
<meta name="description" content="{e(snippet(desc))}">
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
    html = put(html, "footer", footer(lang, page), page)
    html = put(html, "alt", alt(lang, page, html), page)
    return html


# ---------------------------------------------------------------- map and weapon pages
MAP_MORE = {"en": "Full {m} guide", "nl": "Volledige gids voor {m}"}


def map_links(lang, html):
    """On the maps page, a link from each map to its own page."""
    html = re.sub(r'\n        <p class="map-more">.*?</p>', "", html)
    for name in MAPLIST:
        at = html.index("</dl>", html.index('<section class="band map-sec" id="%s">' % name)) + 5
        html = html[:at] + '\n        <p class="map-more"><a class="text-link" href="map-%s.html">%s</a></p>' % (name, MAP_MORE[lang].format(m=name.capitalize())) + html[at:]
    return html


def shell(lang, page, title, desc, og, image, body, extra=""):
    """A whole generated page: head, nav, the given body and the footer."""
    up = upp(lang)
    e = lambda t: htmlmod.escape(t, quote=True)
    html = f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(snippet(desc))}">
<meta name="theme-color" content="#0d1016">
<link rel="canonical" href="{url(lang, page)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url(lang, page)}">
<meta property="og:site_name" content="TrueCombat: Platinum">
<meta property="og:locale" content="{OGLOCALE[lang]}">
<meta property="og:title" content="{e(title.split(' · TrueCombat: Platinum')[0])}">
<meta property="og:description" content="{e(og)}">
<meta property="og:image" content="{SITE}img/{image}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{SITE}img/{image}">
{extra}<!--alt-->
<!--/alt-->
<link rel="icon" type="image/png" href="{up}img/favicon.png">
<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<!--nav-->
<!--/nav-->

<main id="top">
{body}</main>

<!--footer-->
<!--/footer-->

<script src="{up}js/site.js"></script>
</body>
</html>
"""
    html = put(html, "nav", nav(lang, page), page)
    html = put(html, "footer", footer(lang, page), page)
    html = put(html, "alt", alt(lang, page, html), page)
    return html


MATCH = {
    "en": {"title": "Match report · TrueCombat: Platinum", "desc": "A finished TrueCombat: Platinum match: the result, the MVP and the full scoreboard for both teams.",
           "back": "Latest results", "eyebrow": "Match report", "h1": "Match report",
           "lede": "Every finished match on a ranked server gets a page. Open one from the latest results or from a player profile.",
           "missing": "This match could not be found."},
    "nl": {"title": "Wedstrijdverslag · TrueCombat: Platinum", "desc": "Een afgelopen potje TrueCombat: Platinum: de uitslag, de MVP en het volledige scorebord van beide teams.",
           "back": "Laatste uitslagen", "eyebrow": "Wedstrijdverslag", "h1": "Wedstrijdverslag",
           "lede": "Elk afgelopen potje op een ranked server krijgt een eigen pagina. Open er een vanuit de laatste uitslagen of vanuit een spelersprofiel.",
           "missing": "Dit potje is niet gevonden."},
}


def match_page(lang):
    """match.html: an empty frame that js/site.js fills from the stats service (match.json?id=)."""
    T = MATCH[lang]
    up = upp(lang)
    body = f"""<div data-match>
<section class="page-head pf-head">
  <div class="head-art" data-m-art style="--art: url({up}img/media-map-vote.webp); --art-s: url({up}img/media-map-vote-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <a class="pf-back" href="servers.html">\u2190 {T['back']}</a>
    <span class="eyebrow">{T['eyebrow']}</span>
    <h1 data-m-title>{T['h1']}</h1>
    <p class="lede" data-m-lede>{T['lede']}</p>
  </div>
</section>

<section class="band pf-body" data-m-body hidden>
  <div class="wrap pf-grid">
    <div class="m-score" data-m-score></div>
    <div class="pf-stats" data-m-facts></div>
    <div class="m-teams" data-m-teams></div>
    <p class="yt-note pf-foot" data-m-foot></p>
  </div>
</section>

<section class="band" data-m-missing hidden>
  <div class="wrap">
    <p class="lede" data-m-missing-text>{T['missing']}</p>
  </div>
</section>
</div>
"""
    return shell(lang, "match", T["title"], T["desc"], T["desc"], "og-leaderboards.jpg", body, '<meta name="robots" content="noindex, follow">\n')


def detail_pages(lang):
    """(page name, html) for every map page and weapon page in one language."""
    pages = []
    for name in MAPLIST:
        title, desc, og = detail.map_meta(lang, name)
        pages.append(("map-" + name, title, desc, og, "og-map-%s.jpg" % name, detail.map_body(lang, name, MAPLIST, layout_html), ""))
    allw = detail.weapons(lang)
    for w in allw:
        title, desc = detail.weapon_meta(lang, w)
        pages.append(("weapon-" + w["id"], title, desc, desc, "og-weapons.jpg", detail.weapon_body(lang, w, allw, WL[lang]["modes"]), ""))
    out = []
    for page, title, desc, og, image, body, extra in pages:
        if lang != "en":
            body = ASSET.sub(r"../\1/", body)
        html = shell(lang, page, title, desc, og, image, body, extra)
        out.append((page, html))
    return out


# ---------------------------------------------------------------- site search
KIND = {"en": {"page": "Page", "section": "Section", "weapon": "Weapon", "map": "Map", "post": "Devlog", "faq": "Question", "release": "Patch notes"},
        "nl": {"page": "Pagina", "section": "Onderdeel", "weapon": "Wapen", "map": "Map", "post": "Devlog", "faq": "Vraag", "release": "Patchnotes"}}


def search_index(lang, posts):
    """Everything the Ctrl+K search can find: pages, their sections, weapons, maps, devlog posts, FAQ entries and releases."""
    K = KIND[lang]
    base = DOCS / sub(lang)
    rows = []
    def text(s):
        return re.sub(r"\s+", " ", strip_tags(s)).strip()
    for page in [p for p in PAGES if p != "player"] + LANDING:
        # a page the language does not have is listed from the English site
        there = "" if has(lang, page) else "../"
        html = unbust(((base if has(lang, page) else DOCS) / (page + ".html")).read_text(encoding="utf-8"))
        title = text(re.search(r"<title>(.*?)</title>", html, re.S).group(1)).split(" · ")[0]
        if page == "index":
            title = "TrueCombat: Platinum"
        desc = htmlmod.unescape(re.search(r'<meta name="description" content="([^"]*)"', html).group(1))
        rows.append({"t": title, "u": there + href(page), "k": K["page"], "d": desc})
        main = html[html.index("<main"):html.index("</main>")]
        if page == "news":
            for m in re.finditer(r'<details class="release" id="([^"]+)".*?<span class="sum">(.*?)</span>', main, re.S):
                rows.append({"t": m.group(1), "u": there + "news.html#" + m.group(1), "k": K["release"], "d": text(m.group(2))[:150]})
            continue
        if page == "faq":
            for qid, q, a in landing.faq_items(lang):
                rows.append({"t": text(q), "u": "faq.html#" + qid, "k": K["faq"], "d": text(a)[:150]})
            continue
        for m in re.finditer(r'<section[^>]*\bid="([^"]+)"[^>]*>', main):
            h = re.search(r"<h([23])[^>]*>(.*?)</h\1>", main[m.end():m.end() + 1800], re.S)
            if not h:
                continue
            if page == "maps" and m.group(1) in MAPLIST:
                continue
            kind = K["section"]
            rows.append({"t": text(h.group(2)), "u": there + href(page) + "#" + m.group(1), "k": kind, "d": LABELS[lang].get(page, title) if page != "index" else ""})
    weapons = unbust((base / "weapons.html").read_text(encoding="utf-8"))
    for m in re.finditer(r'<article class="[^"]*" id="([^"]+)"[^>]*>.*?<h3[^>]*>(.*?)</h3><span class="full">(.*?)</span>', weapons, re.S):
        rows.append({"t": text(m.group(2)), "u": "weapon-%s.html" % m.group(1), "k": K["weapon"], "d": text(m.group(3))})
    for name in MAPLIST:
        rows.append({"t": name.capitalize(), "u": "map-%s.html" % name, "k": K["map"], "d": detail.map_text(lang, name)[0]})
    for p in posts:
        rows.append({"t": p["title"], "u": ("../" if lang in XLANGS else "") + "devlog-%s.html" % p["slug"], "k": K["post"], "d": p["summary"][:150]})
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
           "## Maps", ""]
    out += ["- [%s](%s): %s" % (n.capitalize(), url("en", "map-" + n), detail.map_text("en", n)[0]) for n in MAPLIST]
    out += ["", "## Weapons", ""]
    out += ["- [%s](%s): %s" % (w["label"], url("en", "weapon-" + w["id"]), detail.weapon_lede("en", w)) for w in detail.weapons("en")]
    out += ["",
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


def to_lang(lang, page, html):
    """An English page in another language: Dutch from nl.py (every pair must match), the extra
    languages from i18n/<code>.py over the same English strings, with English left where one is missing."""
    import nl  # noqa: E402
    pairs = nl.COMMON + nl.PAGES.get(page, [])
    missing = []
    for en, du in pairs:
        if en not in html:
            if (en, du) in nl.COMMON:
                continue
            missing.append(en)
            continue
        to = du if lang == "nl" else i18n.MODS[lang].PAIRS.get(en)
        if to is None:
            UNTRANSLATED.setdefault(lang, []).append((page, en))
            continue
        html = html.replace(en, to)
    if missing:
        sys.exit("nl.py: %s.html no longer contains:\n  " % page + "\n  ".join(m[:90] for m in missing))
    html = html.replace('<html lang="en">', '<html lang="%s">' % lang, 1)
    html = short_months(lang, html)
    html = ASSET.sub(r"../\1/", html)
    html = html.replace('href="style.css"', 'href="../style.css"')
    html = html.replace('content="' + url("en", page) + '"', 'content="' + url(lang, page) + '"')
    html = html.replace('rel="canonical" href="' + url("en", page) + '"', 'rel="canonical" href="' + url(lang, page) + '"')
    html = html.replace('<meta property="og:locale" content="en_GB">', '<meta property="og:locale" content="%s">' % OGLOCALE[lang])
    return html


UNTRANSLATED = {}


def write(lang, page, html):
    """Saves a finished page. The extra languages get their script strings and English links for English-only pages."""
    if lang in XLANGS:
        html = english_links(lang, html)
        # the big download button reads "Download <version>" in English and Dutch
        html = html.replace('<span class="big">Download ', '<span class="big">%s ' % LABELS[lang]["download"])
        html = html.replace('<script src="../js/site.js', '<script src="../js/lang-%s.js"></script>\n<script src="../js/site.js' % lang, 1)
    out = DOCS / sub(lang)
    out.mkdir(exist_ok=True)
    (out / (page + ".html")).write_text(bust(html), encoding="utf-8")


def extend_tables():
    """Gives every string table its entries for the extra languages."""
    for name in ("LABELS", "GAME_DESC", "TEAM", "WL", "LO", "DL", "DEVREACH", "SR", "WS", "MAP_MORE", "MATCH", "KIND", "INSTALL_KIND", "SHORT_MONTHS", "OGLOCALE"):
        i18n.extend(globals()[name], name)
    for code in XLANGS:
        ROAD[code] = tuple(i18n.tx(code, t) for t in ROAD["en"])
        OGLOCALE[code] = i18n.OGLOCALE[code]
    for name in ("DOWNLOAD_T", "FAQ", "ELITE_T", "PRIVACY_T"):
        i18n.extend(getattr(landing, name), name)
    i18n.extend(detail.S, "S")



# ---------------------------------------------------------------- cache busting
# style.css and site.js get ?v=<content hash>, so a deploy never pairs new HTML with a cached old
# stylesheet or script. Sources are read back without the suffix, so the rest of the build is unchanged.
VERSIONED = re.compile(r'((?:href|src)="(?:\.\./)?(?:style\.css|js/site\.js))\?v=[0-9a-f]+"')


def unbust(html):
    return unclean(VERSIONED.sub(r'\1"', SCRIPT_CSP.sub("", html)))


# ---------------------------------------------------------------- script policy
# The VPS header policy still allows inline scripts (pages outside this build carry their own).
# Every built page adds a stricter policy of its own: only site files and the exact inline
# scripts written here may run, so injected markup (an onerror= attribute, a stray <script>)
# never executes. Browsers apply both policies, so the stricter one wins. JSON-LD is data and
# is not affected.
SCRIPT_CSP = re.compile(r'<meta http-equiv="Content-Security-Policy" content="script-src [^"]*">\n')
INLINE_SCRIPT = re.compile(r'<script(?: type="speculationrules")?>(.*?)</script>', re.S)


def script_policy(html):
    import base64
    import hashlib
    html = SCRIPT_CSP.sub("", html)
    hashes = []
    for m in INLINE_SCRIPT.finditer(html):
        h = "'sha256-%s'" % base64.b64encode(hashlib.sha256(m.group(1).encode("utf-8")).digest()).decode("ascii")
        if h not in hashes:
            hashes.append(h)
    meta = '<meta http-equiv="Content-Security-Policy" content="script-src %s">\n' % " ".join(["'self'"] + hashes)
    head = '<meta charset="utf-8">\n'
    if head not in html:
        raise SystemExit("script policy: no <meta charset> line to put the policy after")
    return html.replace(head, head + meta, 1)


# ---------------------------------------------------------------- clean URLs
# The site links to /maps, not /maps.html (the VPS serves {path}.html, GitHub Pages does the same).
# The build itself keeps working with .html names: every page is read back through unclean() and
# every file is written through clean(), so hand-edited English pages and translation pairs may
# use either form.
LINKED = re.compile(r'((?:href="/?|"u": ?"|https://truecombat\.eu/)(?:\.\./)?(?:(?:de|fr|pl|nl)/)?)([a-z0-9][a-z0-9-]*)\.html(?=[#?"<)\s\\])')


def clean(text):
    def one(m):
        if m.group(2) != "index":
            return m.group(1) + m.group(2)
        return m.group(1) if m.group(1).endswith("/") else m.group(1) + "./"
    return LINKED.sub(one, text)


def unclean(html):
    names = "|".join(re.escape(p.stem) for p in sorted(DOCS.glob("*.html"), key=lambda p: -len(p.stem)) if p.stem != "index")
    return re.sub(r'((?:href="/?|https://truecombat\.eu/)(?:\.\./)?(?:(?:de|fr|pl|nl)/)?)(%s)(?=[#?"<)\s\\])' % names, r"\1\2.html", html)


def bust(html):
    html = clean(html)
    import hashlib
    for name, attr in (("style.css", "href"), ("js/site.js", "src")):
        v = hashlib.sha1((DOCS / name).read_bytes()).hexdigest()[:10]
        html = re.sub(r'(%s="(?:\.\./)?%s)"' % (attr, re.escape(name)), r'\1?v=%s"' % v, html)
    return script_policy(html)


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
            old = OLD_LASTMOD.get(clean(SITE + str(path.relative_to(DOCS)).replace("\\", "/").replace("index.html", "")))
            if old:
                return old
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel], cwd=ROOT, capture_output=True, text=True).stdout.strip()
        return out or today
    except (OSError, ValueError):
        return today


def launcher_feed(posts):
    """docs/launcher-feed.txt: the slides and news cards on the launcher's Play page, from launcher.json,
    the current release and the latest devlog post. The launcher only accepts links to the project's own sites."""
    data = json.loads((HERE / "launcher.json").read_text(encoding="utf-8"))
    version = latest_version()

    def one_line(text, limit):
        text = " ".join(strip_tags(inline(text)).split())
        if len(text) <= limit:
            return text
        cut = text[:limit - 1].rsplit(" ", 1)[0].rstrip(",;:")
        return cut + "\u2026"

    def two_lines(title):
        title = title.rstrip(".")
        if "," in title:
            a, b = title.split(",", 1)
            if len(a) + 1 <= 22 and len(b.strip()) + 1 <= 22:
                return a + ",|" + b.strip() + "."
        words = title.split()
        best = None
        for i in range(1, len(words)):
            a, b = " ".join(words[:i]), " ".join(words[i:])
            score = max(len(a), len(b))
            if best is None or score < best[0]:
                best = (score, a + "|" + b + ".")
        return best[1] if best and best[0] <= 22 else None

    def sentences(text, limit):
        text = " ".join(strip_tags(inline(text)).split())
        keep = ""
        for part in re.split(r"(?<=[.!?])\s+", text):
            if len((keep + " " + part).strip()) > limit:
                break
            keep = (keep + " " + part).strip()
        return keep or one_line(text, limit)

    slides = []
    rel = data["releases"].get(version, {})
    slides.append({"eyebrow": "Update " + version, "chip": "Live now",
                   "title": rel.get("title", "Update %s|is live." % version),
                   "text": rel.get("text", "See everything that changed in the latest update."),
                   "button": "Read patch notes", "url": SITE + "news.html",
                   "button2": rel.get("button2", ""), "url2": rel.get("url2", "")})
    post = next((p for p in posts if two_lines(p["title"])), None)
    if post:
        slides.append({"eyebrow": "Devlog", "title": two_lines(post["title"]), "text": sentences(post["summary"], 200),
                       "button": "Read the devlog", "url": "%sdevlog-%s.html" % (SITE, post["slug"])})
    slides += data["slides"]
    news = [{"tag": "Devlog", "title": one_line(posts[0]["title"], 60), "text": sentences(posts[0]["summary"], 150),
             "url": "%sdevlog-%s.html" % (SITE, posts[0]["slug"])}] + data["news"]
    allowed = ("https://truecombat.eu/", "https://github.com/", "https://www.youtube.com/", "https://youtu.be/",
               "https://discord.gg/", "https://ko-fi.com/")
    out = ["# Launcher Play page. Written by tools/website/build.py from tools/website/launcher.json; do not edit."]
    for kind, items, keys in (("slide", slides[:4], ("eyebrow", "chip", "title", "text", "button", "url", "button2", "url2")),
                              ("news", news[:3], ("tag", "title", "text", "url"))):
        for item in items:
            for key in ("url", "url2"):
                if item.get(key) and not item[key].startswith(allowed):
                    sys.exit("launcher.json: %s is not a link the launcher accepts" % item[key])
            out.append("[%s]" % kind)
            out += ["%s=%s" % (k, " ".join(str(item[k]).split())) for k in keys if item.get(k)]
    return "\n".join(out) + "\n"


GO_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
GO_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>TrueCombat: Platinum</title>
<link rel="canonical" href="{canon}">
<meta http-equiv="refresh" content="0; url={target}">
</head>
<body style="background:#0d1016;color:#e8eaef;font:16px system-ui,sans-serif">
<p><a href="{target}" style="color:#e8eaef">TrueCombat: Platinum</a></p>
</body>
</html>
"""


def go_links():
    """truecombat.eu/go/<name>: short campaign links for posts and creators, from golinks.json."""
    from urllib.parse import urlencode
    links = json.loads((HERE / "golinks.json").read_text(encoding="utf-8"))["links"]
    root = DOCS / "go"
    if root.exists():
        for old in root.iterdir():
            if old.is_dir() and old.name not in links:
                for f in old.iterdir():
                    f.unlink()
                old.rmdir()
    for name, ln in sorted(links.items()):
        if not GO_NAME.match(name):
            sys.exit("golinks.json: bad link name %r" % name)
        tags = {"utm_source": ln["source"], "utm_medium": ln.get("medium", ""), "utm_campaign": ln.get("campaign", ""), "utm_content": ln.get("content", "")}
        for k, v in tags.items():
            if v and not re.match(r"^[a-z0-9][a-z0-9._-]{0,39}$", v):
                sys.exit("golinks.json: %s for %r must be lower-case letters, digits, dots, dashes" % (k, name))
        to = ln.get("to", "")
        to = to[:-5] if to.endswith(".html") else to  # the site serves clean addresses (deploy/clean-urls.caddy)
        target = "/" + to + "?" + urlencode({k: v for k, v in tags.items() if v})
        out = root / name
        out.mkdir(parents=True, exist_ok=True)
        (out / "index.html").write_text(GO_PAGE.format(target=htmlmod.escape(target, quote=True), canon=SITE + to), encoding="utf-8")
    return len(links)


def main():
    extend_tables()
    posts = {lang: devlog_posts(lang) for lang in LANGS}
    if [p["slug"] for p in posts["en"]] != [p["slug"] for p in posts["nl"]]:
        sys.exit("devlog: every post needs both an .en.md and an .nl.md file")
    latest = None

    def generated(lang, page, html, path):
        """Fills the blocks this script writes into a hand-edited page."""
        if page == "weapons":
            html = put(html, "weapons", weapons_html(lang), path)
        if page == "index":
            html = put(html, "roadmap", roadmap_html(lang, latest), path)
            html = put(html, "devlog-latest", devlog_latest(lang, posts[lang]), path)
            html = put(html, "devlog-hero", devlog_hero(lang, posts[lang]), path)
            html = put(html, "devlog-home", devlog_home(lang, posts[lang]), path)
        if page == "devlog":
            html = put(html, "devlog", devlog_list(lang, posts[lang]), path)
            html = put(html, "devlog-tags", devlog_tags(lang, posts[lang]), path)
        if page == "maps":
            # the explanation of the plan is the same for every map, so the maps page says it once
            for i, name in enumerate(MAPLIST):
                html = put(html, "layout-" + name, layout_html(lang, name, intro=i == 0), path)
        if page == "studio":
            html = put(html, "studio-releases", studio_releases(lang, "v" + latest_version()), path)
            html = put(html, "studio-devlog", studio_devlog(lang, posts[lang]), path)
            html = put(html, "studio-workshop", studio_workshop(lang, "v" + latest_version()), path)
        if page == "support":
            html = put(html, "support-funding", support_funding(lang), path)
        return html

    for page in PAGES:
        path = DOCS / (page + ".html")
        en = unbust(path.read_text(encoding="utf-8"))
        if page == "index":
            m = re.search(r"data-version>(v[\d.]+)<", en)
            latest = m.group(1) if m else "v0.0.0"
        en = generated("en", page, en, path)
        src = en
        if page == "maps":
            en = map_links("en", en)
        en = put(en, "nav", nav("en", page), path)
        en = put(en, "footer", footer("en", page), path)
        en = put(en, "alt", alt("en", page, en), path)
        path.write_text(bust(en), encoding="utf-8")

        for lang in LANGS[1:]:
            if not has(lang, page):
                continue
            tr = to_lang(lang, page, generated(lang, page, src, path))
            if page == "maps":
                tr = map_links(lang, tr)
            tr = put(tr, "nav", nav(lang, page), path)
            tr = put(tr, "footer", footer(lang, page), path)
            tr = put(tr, "alt", alt(lang, page, tr), path)
            write(lang, page, tr)

    go_links()
    for lang in LANGS:
        for page in LANDING:
            write(lang, page, landing_page(lang, page))
        for page, html in detail_pages(lang):
            write(lang, page, html)
        write(lang, "match", match_page(lang))
    details = [page for page, _ in detail_pages("en")]

    template = unbust((DOCS / "devlog.html").read_text(encoding="utf-8"))
    for lang in ("en", "nl"):
        for post in posts[lang]:
            out = DOCS / sub(lang) / ("devlog-%s.html" % post["slug"])
            out.write_text(bust(devlog_page(lang, post, posts[lang], template)), encoding="utf-8")
        (DOCS / sub(lang) / "devlog.xml").write_text(clean(devlog_feed(lang, posts[lang])), encoding="utf-8")

    for lang in LANGS:
        (DOCS / "js" / ("search-%s.json" % lang)).write_text(clean(search_index(lang, posts[lang])), encoding="utf-8")
    for lang in XLANGS:
        (DOCS / "js" / ("lang-%s.js" % lang)).write_text(
            "/* Written by tools/website/build.py from tools/website/i18n/%s.py. */\nwindow.TCP_L = %s;\n"
            % (lang, json.dumps(i18n.MODS[lang].JS, ensure_ascii=False, separators=(",", ":"))), encoding="utf-8")
    (DOCS / "llms.txt").write_text(clean(llms_txt(posts["en"])), encoding="utf-8")
    (DOCS / "launcher-feed.txt").write_text(launcher_feed(posts["en"]), encoding="utf-8")

    old = DOCS / "sitemap.xml"
    if old.exists():
        OLD_LASTMOD.update(re.findall(r"<url><loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>", old.read_text(encoding="utf-8")))
    rows = []
    # player.html without an id is an empty profile, so only real pages go in the sitemap
    for page in [p for p in PAGES if p != "player"] + LANDING + details + ["devlog-" + p["slug"] for p in posts["en"]]:
        alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l, url(l, page)) for l in langs_for(page))
        for lang in langs_for(page):
            path = DOCS / sub(lang) / (page + ".html")
            images = "".join("<image:image><image:loc>%s%s</image:loc></image:image>" % (SITE, i) for i in page_images(path))
            rows.append("  <url><loc>%s</loc><lastmod>%s</lastmod>%s%s</url>" % (url(lang, page), lastmod(path), alts, images))
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
        + clean("\n".join(rows)) + "\n</urlset>\n", encoding="utf-8")
    # hand-written pages (join, devlog-stats, 404, ...) get the same script policy as built ones
    for path in sorted(DOCS.rglob("*.html")):
        html = path.read_text(encoding="utf-8")
        if INLINE_SCRIPT.search(html) and '<meta charset="utf-8">\n' in html:
            done = script_policy(html)
            if done != html:
                path.write_text(done, encoding="utf-8")
    left = {lang: len(v) for lang, v in UNTRANSLATED.items()}
    print("built %d pages in %s%s" % (len(PAGES) + len(LANDING) + len(details) + 1, ", ".join(LANGS),
                                      "; still in English: %s" % left if left else ""))


if __name__ == "__main__":
    main()
