"""One page per map (map-<name>.html) and per weapon (weapon-<id>.html), in every site language.

build.py writes these in full. Nothing here is hand-edited HTML: the figures come from
weapons.json and maplayouts.json, the map descriptions from nl.py's _MAPS table, and the
sentences from the S table below, so a new language only needs a new entry in S.
"""
import html as htmlmod
import json
import math
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent

S = {
    "en": {
        "map": "Map", "maps": "Maps", "weapons": "Weapons", "layout": "Layout",
        "map_title": "{m} map: layout, callouts and bomb sites · TrueCombat: Platinum",
        "map_desc": "{m} ({file}) in TrueCombat: Platinum: overhead layout, bomb sites, flags, spawns and location names for the TrueCombat: Elite map. {d}",
        "glance": "At a glance", "file": "File", "setting": "Setting", "light": "Light", "sites": "Bomb sites", "flags": "Flags",
        "spawns": "Spawn points", "spawns_v": "{t} Terrorist, {s} SpecOps", "names": "Location names", "gmodes": "Game modes", "modes_v": "All seven",
        "flags_v": "One per team",
        "callouts_h": "Location names on {m}",
        "callouts_p": "These are the game's own names for each part of {m}. Use them when you call out a position, and everyone on the server knows where you mean.",
        "nocall": "{m} has no location names in the game, so teams make up their own.",
        "play_h": "Playing {m}",
        "bomb_b": "Bomb.",
        "bomb": "Terrorists plant at site A{an} or site B{bn}, and SpecOps defend or defuse. {near}",
        "near_split": "Measured in a straight line, site {a} is nearer the SpecOps spawn and site {b} nearer the Terrorist spawn.",
        "near_same": "Measured in a straight line, both sites are nearer the {team} spawn: site {a} is the close one and site {b} the far one.",
        "flag_b": "Flag Capture.", "flag": "Each team guards a backpack near its own spawn. Steal the other one and carry it home. First team to three wins.",
        "elim_b": "Elimination and Team Elimination.", "elim": "One life per round. With {n} spawn points a side, a full server still starts spread out.",
        "tdm_b": "Team Deathmatch.", "tdm": "Respawns on, first team to 20 kills.",
        "hd_h": "Stock and HD textures", "hd_p": "Drag to compare the same spot and frame: the original textures against the HD set.",
        "stock": "Stock", "hd_alt": "{m}, {spot}, with HD textures", "stock_alt": "{m}, {spot}, with stock textures", "divider": "{m} comparison divider position",
        "more_maps": "More maps", "all_maps": "All six maps", "shot_alt": "{m} in DirectX 12",
        "play_cta": "Play {m}", "play_cta_p": "Host it from the launcher or find it in the rotation on the official servers.", "download": "Download", "servers": "Find a server",
        "terrorists": "Terrorist", "specops": "SpecOps",
        "w_title": "{n}: damage, fire rate and stats · TrueCombat: Platinum",
        "w_title_eq": "{n} ({full}) · TrueCombat: Platinum",
        "w_desc": "{n} in TrueCombat: Platinum: {dmg} damage, {rpm} rpm, {clip}-round magazine, {reload} s reload. Original TrueCombat: Elite values, compared with every other weapon in its class.",
        "w_desc_eq": "{n} ({full}) in TrueCombat: Platinum. {note}",
        "team_specops": "SpecOps", "team_terror": "Terrorists", "team_both": "both teams",
        "lede": "The {n} is a {slot} weapon for {team}, chambered in {cal}. It deals {dmg} damage per hit at {rpm} rounds per minute, from a magazine of {clip}.",
        "lede_pellets": "The {n} is a {slot} weapon for {team}, in {cal}. Each shell spreads {dmg} damage over 9 pellets, and it reloads one shell at a time.",
        "lede_eq": "{full}, carried by {team}. {note}",
        "slot_primary": "primary", "slot_secondary": "secondary",
        "stats": "Figures", "damage": "Damage per hit", "rpm": "Fire rate", "rpm_u": "rpm", "mag": "Magazine", "reserve": "Reserve", "reload": "Reload",
        "reload_shell": "{s} s per shell", "caliber": "Calibre", "slot": "Slot", "team": "Carried by", "modes": "Fire modes", "scope": "Scope", "sound": "Sound",
        "suppressed": "Suppressed", "subsonic": "Subsonic rounds", "empty": "Time to empty", "mag_dmg": "Damage per magazine", "dps": "Damage while firing",
        "dps_u": "per second", "sec": "s", "rounds": "{n} rounds",
        "source": "Figures are the TrueCombat: Elite 0.49b values that Platinum is built on. Damage is per hit, before head, body or leg modifiers.",
        "rank_h": "How it compares", "rank": "Among the {n} {group}, the {w} has {list}.", "rank_mid": "Among the {n} {group}, the {w} sits with the pack on damage, fire rate and magazine size. The table shows where the others differ.",
        "and": " and ",
        "top": ["the highest damage per hit", "the highest fire rate", "the largest magazine"],
        "top_tie": ["the joint-highest damage per hit", "the joint-highest fire rate", "the joint-largest magazine"],
        "low": ["the lowest damage per hit", "the lowest fire rate", "the smallest magazine"],
        "low_tie": ["the joint-lowest damage per hit", "the joint-lowest fire rate", "the joint-smallest magazine"],
        "class_h": "Every weapon in the class", "weapon": "Weapon", "this": "this page",
        "g_pistols": "pistols", "g_smgs": "submachine guns", "g_rifles": "rifles and carbines", "g_shotguns": "shotguns", "g_snipers": "sniper rifles", "g_equipment": "equipment",
        "compare_cta": "Compare weapons side by side", "all_weapons": "All weapons", "prev": "Previous", "next": "Next",
        "toc": "On this page",
    },
    "nl": {
        "map": "Map", "maps": "Maps", "weapons": "Wapens", "layout": "Plattegrond",
        "map_title": "Map {m}: plattegrond, locatienamen en bomplekken · TrueCombat: Platinum",
        "map_desc": "{m} ({file}) in TrueCombat: Platinum: plattegrond, bomplekken, vlaggen, spawns en locatienamen van de TrueCombat: Elite-map. {d}",
        "glance": "In het kort", "file": "Bestand", "setting": "Omgeving", "light": "Licht", "sites": "Bomplekken", "flags": "Vlaggen",
        "spawns": "Spawnpunten", "spawns_v": "{t} Terroristen, {s} SpecOps", "names": "Locatienamen", "gmodes": "Spelmodi", "modes_v": "Alle zeven",
        "flags_v": "Eén per team",
        "callouts_h": "Locatienamen op {m}",
        "callouts_p": "Dit zijn de namen die het spel zelf aan elk deel van {m} geeft. Gebruik ze als je een positie doorgeeft, dan weet iedereen op de server waar je bedoelt.",
        "nocall": "{m} heeft geen locatienamen in het spel, dus teams bedenken hun eigen namen.",
        "play_h": "{m} spelen",
        "bomb_b": "Bomb.",
        "bomb": "Terroristen plaatsen de bom bij plek A{an} of plek B{bn}, en SpecOps verdedigen of ontmantelen. {near}",
        "near_split": "In rechte lijn gemeten ligt plek {a} dichter bij de spawn van SpecOps en plek {b} dichter bij die van de Terroristen.",
        "near_same": "In rechte lijn gemeten liggen beide plekken dichter bij de spawn van {team}: plek {a} is de dichtste en plek {b} de verste.",
        "flag_b": "Flag Capture.", "flag": "Elk team bewaakt een rugzak bij de eigen spawn. Steel die van de ander en breng hem naar huis. Het eerste team met drie wint.",
        "elim_b": "Elimination en Team Elimination.", "elim": "Eén leven per ronde. Met {n} spawnpunten per kant begint ook een volle server verspreid.",
        "tdm_b": "Team Deathmatch.", "tdm": "Met respawns, het eerste team met 20 kills wint.",
        "hd_h": "Standaard- en HD-textures", "hd_p": "Sleep om dezelfde plek en hetzelfde beeld te vergelijken: de originele textures tegenover de HD-set.",
        "stock": "Standaard", "hd_alt": "{m}, {spot}, met HD-textures", "stock_alt": "{m}, {spot}, met standaardtextures", "divider": "{m}: positie van de vergelijkingslijn",
        "more_maps": "Meer maps", "all_maps": "Alle zes maps", "shot_alt": "{m} in DirectX 12",
        "play_cta": "Speel {m}", "play_cta_p": "Host de map vanuit de launcher of vind hem in de rotatie op de officiële servers.", "download": "Download", "servers": "Vind een server",
        "terrorists": "Terroristen", "specops": "SpecOps",
        "w_title": "{n}: schade, vuursnelheid en statistieken · TrueCombat: Platinum",
        "w_title_eq": "{n} ({full}) · TrueCombat: Platinum",
        "w_desc": "{n} in TrueCombat: Platinum: {dmg} schade, {rpm} spm, magazijn van {clip}, herladen in {reload} s. Originele waarden uit TrueCombat: Elite, vergeleken met elk ander wapen in zijn klasse.",
        "w_desc_eq": "{n} ({full}) in TrueCombat: Platinum. {note}",
        "team_specops": "SpecOps", "team_terror": "de Terroristen", "team_both": "beide teams",
        "lede": "De {n} is een {slot} wapen voor {team}, in kaliber {cal}. Hij doet {dmg} schade per treffer bij {rpm} schoten per minuut, uit een magazijn van {clip}.",
        "lede_pellets": "De {n} is een {slot} wapen voor {team}, in {cal}. Elke patroon verdeelt {dmg} schade over 9 hagels, en hij laadt patroon voor patroon.",
        "lede_eq": "{full}, gedragen door {team}. {note}",
        "slot_primary": "primair", "slot_secondary": "secundair",
        "stats": "Cijfers", "damage": "Schade per treffer", "rpm": "Vuursnelheid", "rpm_u": "spm", "mag": "Magazijn", "reserve": "Reserve", "reload": "Herladen",
        "reload_shell": "{s} s per patroon", "caliber": "Kaliber", "slot": "Slot", "team": "Gedragen door", "modes": "Vuurstanden", "scope": "Vizier", "sound": "Geluid",
        "suppressed": "Geluiddemper", "subsonic": "Subsonische munitie", "empty": "Magazijn leeg in", "mag_dmg": "Schade per magazijn", "dps": "Schade tijdens vuren",
        "dps_u": "per seconde", "sec": "s", "rounds": "{n} patronen",
        "source": "De cijfers zijn de waarden uit TrueCombat: Elite 0.49b waarop Platinum is gebouwd. Schade is per treffer, voor de modificatie voor hoofd, romp of benen.",
        "rank_h": "Hoe hij zich verhoudt", "rank": "Van de {n} {group} heeft de {w} {list}.", "rank_mid": "Van de {n} {group} zit de {w} in de middenmoot voor schade, vuursnelheid en magazijn. De tabel laat zien waar de andere afwijken.",
        "and": " en ",
        "top": ["de hoogste schade per treffer", "de hoogste vuursnelheid", "het grootste magazijn"],
        "top_tie": ["de gedeeld hoogste schade per treffer", "de gedeeld hoogste vuursnelheid", "het gedeeld grootste magazijn"],
        "low": ["de laagste schade per treffer", "de laagste vuursnelheid", "het kleinste magazijn"],
        "low_tie": ["de gedeeld laagste schade per treffer", "de gedeeld laagste vuursnelheid", "het gedeeld kleinste magazijn"],
        "class_h": "Elk wapen in de klasse", "weapon": "Wapen", "this": "deze pagina",
        "g_pistols": "pistolen", "g_smgs": "machinepistolen", "g_rifles": "geweren en karabijnen", "g_shotguns": "hagelgeweren", "g_snipers": "sluipschuttersgeweren", "g_equipment": "uitrusting",
        "compare_cta": "Vergelijk wapens naast elkaar", "all_weapons": "Alle wapens", "prev": "Vorige", "next": "Volgende",
        "toc": "Op deze pagina",
    },
}

e = lambda s: htmlmod.escape(str(s), quote=True)


# ---------------------------------------------------------------- maps
def map_rows():
    import nl
    return {m[0]: m for m in nl._MAPS}


def map_text(lang, name):
    """(description, setting, light, comparison spot) for a map in the given language."""
    import i18n
    m = map_rows()[name]
    if lang == "nl":
        return m[2], m[4], m[6], m[8]
    return tuple(i18n.tx(lang, t) for t in (m[1], m[3], m[5], m[7]))


def caliber(lang, cal):
    """12 gauge is the one calibre whose name changes with the language."""
    import i18n
    return cal.replace("12 gauge", "kaliber 12") if lang == "nl" else i18n.tx(lang, cal)


def local(lang, w, key, default=""):
    """A weapon field in the language: its own _nl entry, the i18n translation of the English, or the English."""
    import i18n
    en = w.get(key + "_en", w.get(key, default))
    return w.get(key + "_" + lang) or (en if lang == "nl" else i18n.tx(lang, en))


def centroid(pts):
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def site_note(T, d):
    """Which bomb site each team reaches first, from the spawn and site positions in the map file."""
    if len(d["sites"]) != 2:
        return ""
    so, te = centroid(d["spawns"]["specops"]), centroid(d["spawns"]["terrorists"])
    closer, dist = [], []
    for s in d["sites"]:
        c = ((s["a"][0] + s["b"][0]) / 2, (s["a"][1] + s["b"][1]) / 2)
        closer.append("specops" if math.dist(c, so) < math.dist(c, te) else "terrorists")
        dist.append(math.dist(c, so if closer[-1] == "specops" else te))
    names = [s["site"] for s in d["sites"]]
    if closer[0] != closer[1]:
        a, b = names if closer[0] == "specops" else names[::-1]
        return T["near_split"].format(a=a, b=b)
    a, b = names if dist[0] <= dist[1] else names[::-1]
    return T["near_same"].format(team=T[closer[0]], a=a, b=b)


def map_meta(lang, name):
    T = S[lang]
    m = name.capitalize()
    desc = map_text(lang, name)[0]
    return T["map_title"].format(m=m), T["map_desc"].format(m=m, file="obj_" + name, d=desc.split(". ")[0].rstrip(".") + "."), desc


def map_body(lang, name, maplist, layout_html):
    T = S[lang]
    m = name.capitalize()
    d = json.loads((HERE / "maplayouts.json").read_text(encoding="utf-8"))[name]
    desc, setting, light, spot = map_text(lang, name)
    sites = ", ".join("%s%s" % (s["site"], " (%s)" % e(s["name"]) if s.get("name") else "") for s in d["sites"])
    nm = lambda s: " (%s)" % e(s["name"]) if s.get("name") else ""
    n_t, n_s = len(d["spawns"]["terrorists"]), len(d["spawns"]["specops"])
    if d["callouts"]:
        names = sorted({c["name"] for c in d["callouts"]})
        callouts = '<p>%s</p>\n        <ul class="name-list">%s</ul>' % (T["callouts_p"].format(m=m), "".join("<li>%s</li>" % e(n) for n in names))
    else:
        callouts = "<p>%s</p>" % T["nocall"].format(m=m)
    bomb = T["bomb"].format(an=nm(d["sites"][0]), bn=nm(d["sites"][1]), near=site_note(T, d)) if len(d["sites"]) == 2 else ""
    others = "".join(
        '<a class="map-card" href="map-%s.html"><img src="img/map-%s-640.webp" alt="" width="640" height="360" loading="lazy"><span><b>%s</b><small>%s</small></span></a>'
        % (o, o, o.capitalize(), e(map_text(lang, o)[1])) for o in maplist if o != name)
    return f"""<section class="page-head">
  <div class="head-art" style="--art: url(img/map-{name}.webp); --art-s: url(img/map-{name}-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <span class="eyebrow">{T['map']}</span>
    <h1>{m}</h1>
    <p class="lede">{e(desc)}</p>
    <nav class="chips" aria-label="{T['toc']}"><a href="#layout">{T['layout']}</a><a href="#names">{T['names']}</a><a href="#play">{T['gmodes']}</a><a href="#textures">HD</a></nav>
  </div>
</section>

<section class="band">
  <div class="wrap">
    <div class="map-grid">
      <div class="vf"><img src="img/map-{name}.webp" srcset="img/map-{name}-640.webp 640w, img/map-{name}.webp 1280w" sizes="(max-width: 900px) 100vw, 700px" alt="{T['shot_alt'].format(m=m)}" width="1280" height="720"></div>
      <div class="map-info">
        <span class="eyebrow">{T['glance']}</span>
        <dl class="map-facts">
          <dt>{T['file']}</dt><dd class="mono">obj_{name}</dd>
          <dt>{T['setting']}</dt><dd>{e(setting)}</dd>
          <dt>{T['light']}</dt><dd>{e(light)}</dd>
          <dt>{T['sites']}</dt><dd>{sites}</dd>
          <dt>{T['flags']}</dt><dd>{T['flags_v']}</dd>
          <dt>{T['spawns']}</dt><dd>{T['spawns_v'].format(t=n_t, s=n_s)}</dd>
          <dt>{T['names']}</dt><dd>{len(d['callouts'])}</dd>
          <dt>{T['gmodes']}</dt><dd>{T['modes_v']}</dd>
        </dl>
      </div>
    </div>
    <div id="layout" class="anchor">
{layout_html(lang, name).replace('<h3>', '<h2 class="h3">', 1).replace('</h3>', '</h2>', 1)}
    </div>
  </div>
</section>

<section class="band band-alt" id="names">
  <div class="wrap narrow">
    <div class="section-head"><span class="eyebrow">{T['names']}</span><h2>{T['callouts_h'].format(m=m)}</h2></div>
    <div class="prose-block">
        {callouts}
    </div>
  </div>
</section>

<section class="band" id="play">
  <div class="wrap narrow">
    <div class="section-head"><span class="eyebrow">{T['gmodes']}</span><h2>{T['play_h'].format(m=m)}</h2></div>
    <ul class="mode-list">
      <li><b>{T['bomb_b']}</b> {bomb}</li>
      <li><b>{T['flag_b']}</b> {T['flag']}</li>
      <li><b>{T['elim_b']}</b> {T['elim'].format(n=min(n_t, n_s))}</li>
      <li><b>{T['tdm_b']}</b> {T['tdm']}</li>
    </ul>
  </div>
</section>

<section class="band" id="textures">
  <div class="wrap">
    <div class="map-hd">
      <div class="map-hd-copy">
        <h2>{T['hd_h']}</h2>
        <p>{T['hd_p']}</p>
      </div>
      <div class="vf">
        <div class="compare" style="--pos:50%; aspect-ratio: 16 / 9">
          <img src="img/maps/{name}-hd.webp" alt="{e(T['hd_alt'].format(m=m, spot=spot))}" width="1280" height="720" loading="lazy">
          <img class="top" src="img/maps/{name}-stock.webp" alt="{e(T['stock_alt'].format(m=m, spot=spot))}" width="1280" height="720" loading="lazy">
          <span class="tag l">{T['stock']}</span>
          <span class="tag r">HD</span>
          <span class="handle"></span>
          <input type="range" min="0" max="100" value="50" aria-label="{e(T['divider'].format(m=m))}">
        </div>
      </div>
    </div>
  </div>
</section>

<section class="band band-alt">
  <div class="wrap">
    <div class="section-head head-row">
      <div><span class="eyebrow">{T['more_maps']}</span><h2>{T['play_cta'].format(m=m)}</h2><p class="lede">{T['play_cta_p']}</p></div>
      <div class="hero-cta"><a class="btn btn-play" href="download.html"><span class="stack"><span class="big">{T['download']}</span></span></a><a class="btn btn-ghost" href="servers.html">{T['servers']}</a><a class="btn btn-ghost" href="maps.html">{T['all_maps']}</a></div>
    </div>
    <div class="map-cards five">{others}</div>
  </div>
</section>
"""


# ---------------------------------------------------------------- weapons
def wid(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def weapons(lang):
    """Every weapon as a flat list, each with its page id, group and display names for the language."""
    data = json.loads((HERE / "weapons.json").read_text(encoding="utf-8"))
    out, used = [], set()
    for g in data["groups"]:
        for w in g["weapons"]:
            i = wid(w["name"])
            if i in used:
                i += "-" + w["team"]
            used.add(i)
            out.append(dict(w, id=i, group=g["id"], group_title=local(lang, g, "title"),
                            label=local(lang, w, "name"), full_label=local(lang, w, "full")))
    return out


def rpm(w):
    return round(60000 / w["cycle"])


def num(x, lang):
    s = ("%.1f" % x).rstrip("0").rstrip(".")
    return s.replace(".", ",") if lang != "en" else s


def weapon_meta(lang, w):
    T = S[lang]
    if "damage" not in w:
        note = re.sub(r"<[^>]+>", "", local(lang, w, "note"))
        return T["w_title_eq"].format(n=w["label"], full=w["full_label"]), T["w_desc_eq"].format(n=w["label"], full=w["full_label"], note=note)
    return (T["w_title"].format(n=w["label"], full=w["full_label"]),
            T["w_desc"].format(n=w["label"], dmg=w["damage"], rpm=rpm(w), clip=w["clip"], reload=num(w["reload"] / 1000, lang)))


def weapon_lede(lang, w, html=False):
    """The opening sentence. Equipment notes carry a little markup (<kbd>), kept only when html is set."""
    T = S[lang]
    team = T["team_" + w["team"]]
    if "damage" not in w:
        note = local(lang, w, "note")
        return T["lede_eq"].format(full=e(w["full_label"]) if html else w["full_label"], team=team, note=note if html else re.sub(r"<[^>]+>", "", note))
    key = "lede_pellets" if w.get("pellets") else "lede"
    cal = caliber(lang, w["caliber"])
    return T[key].format(n=w["label"], slot=T["slot_" + w["slot"]], team=team, cal=cal, dmg=w["damage"], rpm=rpm(w), clip=w["clip"])


def weapon_body(lang, w, allw, modes):
    T = S[lang]
    team = T["team_" + w["team"]]
    team = team[:1].upper() + team[1:]
    group = [x for x in allw if x["group"] == w["group"]]
    i = allw.index(w)
    prev, nxt = allw[i - 1], allw[(i + 1) % len(allw)]
    mode_tags = "".join("<span>%s</span>" % modes[m] for m in w["modes"])
    rows = [(T["team"], team), (T["modes"], '<span class="wmodes">%s</span>' % mode_tags)]
    extra = ""
    if "damage" in w:
        reload_v = T["reload_shell"].format(s=num(w["reload"] / 1000, lang)) if w.get("shell") else "%s %s" % (num(w["reload"] / 1000, lang), T["sec"])
        rows = [
            (T["damage"], str(w["damage"]) + (" (9 × %s)" % num(w["damage"] / 9, lang) if w.get("pellets") else "")),
            (T["rpm"], "%d %s" % (rpm(w), T["rpm_u"])),
            (T["mag"], T["rounds"].format(n=w["clip"])),
            (T["reserve"], T["rounds"].format(n=w["reserve"])),
            (T["reload"], reload_v),
            (T["empty"], "%s %s" % (num(w["clip"] * w["cycle"] / 1000, lang), T["sec"])),
            (T["mag_dmg"], "{:,}".format(w["damage"] * w["clip"]).replace(",", {"en": ",", "nl": ".", "de": "."}.get(lang, "\u202f"))),
            (T["dps"], "%d %s" % (round(w["damage"] * 1000 / w["cycle"]), T["dps_u"])),
            (T["caliber"], e(w["caliber"].replace(" gauge", "") if lang == "nl" else caliber(lang, w["caliber"]))),
            (T["slot"], T["slot_" + w["slot"]].capitalize()),
        ] + rows
        if w.get("scope"):
            rows.append((T["scope"], e(w["scope"])))
        if w.get("suppressed") or w.get("subsonic"):
            rows.append((T["sound"], ", ".join(x for x in (T["suppressed"] if w.get("suppressed") else "", T["subsonic"] if w.get("subsonic") else "") if x)))
        armed = [x for x in group if "damage" in x]
        rank = ""
        if len(armed) > 1:
            notes = []
            for n, key in enumerate((lambda x: x["damage"], rpm, lambda x: x["clip"])):
                vals = [key(x) for x in armed]
                if min(vals) == max(vals):
                    continue
                # a value most of the class shares is the norm, not something to point out
                if vals.count(key(w)) * 2 > len(vals):
                    continue
                if key(w) == max(vals):
                    notes.append(T["top" if vals.count(max(vals)) == 1 else "top_tie"][n])
                elif key(w) == min(vals):
                    notes.append(T["low" if vals.count(min(vals)) == 1 else "low_tie"][n])
            args = dict(n=len(armed), group=T["g_" + w["group"]], w=e(w["label"]))
            if notes:
                rank = "<p>%s</p>" % T["rank"].format(list=", ".join(notes[:-1]) + (T["and"] if len(notes) > 1 else "") + notes[-1], **args)
            else:
                rank = "<p>%s</p>" % T["rank_mid"].format(**args)
        table = "\n".join(
            '              <tr%s><th scope="row">%s</th><td>%d</td><td>%d</td><td>%d / %d</td><td>%s</td></tr>' % (
                ' class="here"' if x is w else "",
                ('<span>%s</span>' % e(x["label"])) if x is w else '<a href="weapon-%s.html">%s</a>' % (x["id"], e(x["label"])),
                x["damage"], rpm(x), x["clip"], x["reserve"], num(x["reload"] / 1000, lang))
            for x in armed)
        extra = f"""
<section class="band band-alt" id="compare">
  <div class="wrap narrow">
    <div class="section-head"><span class="eyebrow">{e(w['group_title'])}</span><h2>{T['rank_h']}</h2></div>
    <div class="prose-block">{rank}</div>
    <div class="vs-scroll">
      <table class="wtable">
        <thead><tr><th scope="col">{T['weapon']}</th><th scope="col">{T['damage']}</th><th scope="col">{T['rpm']}</th><th scope="col">{T['mag']}</th><th scope="col">{T['reload']} ({T['sec']})</th></tr></thead>
        <tbody>
{table}
        </tbody>
      </table>
    </div>
    <p class="yt-note">{T['source']}</p>
  </div>
</section>
"""
    facts = "\n".join("          <dt>%s</dt><dd>%s</dd>" % r for r in rows)
    return f"""<section class="page-head">
  <div class="head-art" style="--art: url(img/media-grenade.webp); --art-s: url(img/media-grenade-640.webp)" aria-hidden="true"></div>
  <div class="wrap">
    <a class="back" href="weapons.html#{w['group']}">{e(w['group_title'])}</a>
    <h1>{e(w['label'])}</h1>
    <p class="lede">{weapon_lede(lang, w, True) if "damage" not in w else e(weapon_lede(lang, w))}</p>
  </div>
</section>

<section class="band">
  <div class="wrap narrow">
    <div class="section-head"><span class="eyebrow">{T['stats']}</span><h2>{e(w['full_label'])}</h2></div>
    <dl class="facts wfacts">
{facts}
    </dl>
  </div>
</section>
{extra}
<section class="band">
  <div class="wrap narrow">
    <nav class="post-pager">
      <a class="prev" href="weapon-{prev['id']}.html"><small>{T['prev']}</small>{e(prev['label'])}</a>
      <a class="next" href="weapon-{nxt['id']}.html"><small>{T['next']}</small>{e(nxt['label'])}</a>
    </nav>
    <p class="more-row"><a class="btn btn-ghost" href="weapons.html">{T['all_weapons']}</a></p>
  </div>
</section>
"""
