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
  4. writes docs/sitemap.xml.

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

PAGES = ["index", "maps", "weapons", "media", "guide", "servers", "leaderboards", "player", "news", "press", "studio"]

LABELS = {
    "en": {
        "maps": "Maps", "weapons": "Weapons", "guide": "Guide", "servers": "Servers",
        "leaderboards": "Leaderboards", "news": "News", "press": "Press kit", "media": "Media", "studio": "Studio",
        "gallery": "Gallery", "graphics": "Graphics", "faq": "FAQ", "about": "About",
        "download": "Download", "menu": "Menu", "sections": "Sections", "discord": "Join the Discord",
        "other": "Nederlands", "other_short": "NL", "footer": "Footer", "releases": "Releases",
        "dev": "TrueCombat: Platinum is developed by RaziC*.", "rss": "Patch notes (RSS)",
        "legal1": "TrueCombat: Elite was created by Team Terminator. Wolfenstein: Enemy Territory is by Splash Damage and id Software, published by Activision. TrueCombat: Platinum is a fan project and is not affiliated with or endorsed by them.",
        "legal2": "Engine code is released under the GPL. Original game data and artwork keep their original terms; see the licenses folder in each download.",
    },
    "nl": {
        "maps": "Maps", "weapons": "Wapens", "guide": "Gids", "servers": "Servers",
        "leaderboards": "Ranglijsten", "news": "Nieuws", "press": "Perskit", "media": "Media", "studio": "Studio",
        "gallery": "Galerij", "graphics": "Graphics", "faq": "Vragen", "about": "Over",
        "download": "Download", "menu": "Menu", "sections": "Onderdelen", "discord": "Word lid van de Discord",
        "other": "English", "other_short": "EN", "footer": "Voettekst", "releases": "Releases",
        "dev": "TrueCombat: Platinum wordt ontwikkeld door RaziC*.", "rss": "Patchnotes (RSS)",
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
    main = ["maps", "weapons", "media", "guide", "servers", "leaderboards", "news", "studio"]
    active = "leaderboards" if current == "player" else current
    links = "\n".join(
        '      <li><a href="%s"%s>%s</a></li>' % (href(p), ' aria-current="page"' if p == active else "", L[p])
        for p in main)
    menu = "".join('<a href="%s">%s</a>' % (href(p), L[p]) for p in main)
    menu += '<hr><a href="%s">%s</a><a href="%s#graphics">%s</a><a href="%s#faq">%s</a><a href="%s">%s</a><a href="%s">Discord</a><a href="%s" hreflang="%s" lang="%s">%s</a>' % (
        href("media"), L["gallery"], home, L["graphics"], home, L["faq"], href("press"), L["press"], DISCORD, other_href, other, other, L["other"])
    return f"""<!--nav-->
<header class="nav">
  <div class="wrap">
    <a class="nav-brand" href="{home}"><img src="{up}img/team-terminus.webp" alt="" width="30" height="30">TrueCombat <b>Platinum</b></a>
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


def footer(lang):
    L = LABELS[lang]
    up = "../" if lang == "nl" else ""
    items = [(DISCORD, "Discord"), (GITHUB, "GitHub"), (GITHUB + "/releases", L["releases"]), (FEED, L["rss"])]
    items += [(href(p), L[p]) for p in ["maps", "weapons", "media", "guide", "servers", "leaderboards", "news", "studio", "press"]]
    items.append(("./#download", L["download"]))
    links = "\n".join('        <a href="%s">%s</a>' % (h, t) for h, t in items)
    return f"""<!--footer-->
<footer>
  <div class="wrap">
    <div class="foot">
      <img src="{up}img/team-terminus.webp" alt="Team Terminus" width="320" height="320" loading="lazy">
      <div class="who">
        <b>Team Terminus</b>
        <span>{L['dev']}</span>
      </div>
      <nav aria-label="{L['footer']}">
{links}
      </nav>
    </div>
    <div class="legal">
      <p>{L['legal1']}</p>
      <p>{L['legal2']}</p>
    </div>
  </div>
</footer>
<!--/footer-->"""


def alt(lang, page):
    L = LABELS[lang]
    return ("<!--alt-->\n"
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
            else:
                stats = '<p>%s</p>' % w["note_" + lang]
                note = ""
                cls = "wcard equip"
            cards.append(
                f'<article class="{cls}" data-team="{w["team"]}"><header><h3>{htmlmod.escape(w.get("name_" + lang, w["name"]))}</h3><span class="full">{htmlmod.escape(w.get("full_" + lang, w["full"]))}</span></header>'
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
        src = en
        en = put(en, "nav", nav("en", page), path)
        en = put(en, "footer", footer("en"), path)
        en = put(en, "alt", alt("en", page), path)
        path.write_text(en, encoding="utf-8")

        du = src
        if page == "index":
            du = put(du, "roadmap", roadmap_html("nl", latest), path)
        if page == "weapons":
            du = put(du, "weapons", weapons_html("nl"), path)
        du = to_dutch(page, du)
        du = put(du, "nav", nav("nl", page), path)
        du = put(du, "footer", footer("nl"), path)
        du = put(du, "alt", alt("nl", page), path)
        (DOCS / "nl" / (page + ".html")).write_text(du, encoding="utf-8")

    rows = []
    for page in PAGES:
        for lang in ("en", "nl"):
            alts = "".join('<xhtml:link rel="alternate" hreflang="%s" href="%s"/>' % (l, url(l, page)) for l in ("en", "nl"))
            rows.append("  <url><loc>%s</loc>%s</url>" % (url(lang, page), alts))
    (DOCS / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
        + "\n".join(rows) + "\n</urlset>\n", encoding="utf-8")
    print("built %d pages in English and Dutch" % len(PAGES))


if __name__ == "__main__":
    main()
