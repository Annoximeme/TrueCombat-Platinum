"""The Briefing release post: parsing the release body, picking headlines, the layout and its banner."""

import io
import json
import pathlib

import discord
from PIL import Image

from tcpbot import briefing as B
from tcpbot import cards

HERE = pathlib.Path(__file__).parent
BODY = (HERE / "fixtures" / "release-0.38.0.md").read_text(encoding="utf-8")
SITE = "https://truecombat.eu"
REL = {"id": 9, "tag_name": "v0.38.0-sandbox34", "name": "TrueCombat: Platinum v0.38.0", "body": BODY, "assets": []}


def walk(components):
    for c in components:
        yield c
        for key in ("components",):
            yield from walk(c.get(key) or [])
        if c.get("accessory"):
            yield c["accessory"]


def texts(view) -> list[str]:
    return [c["content"] for c in walk(view.to_components()) if c.get("type") == 10]


def test_parse_title_case_sections_and_leads():
    p = B.parse(BODY)
    assert p["header"][0].startswith("TRUECOMBAT: PLATINUM") and len(p["header"]) == 3
    assert p["intro"].startswith("Our biggest update yet.")
    titles = [s["title"] for s in p["sections"]]
    assert titles == ["Experimental: TrueCombat: CQB comes to Platinum", "New Features", "Aim and Performance",
                      "Firefights", "HUD", "Weapons and Visuals", "Bots", "Launcher and Installer",
                      "Fixes and Stability"]
    cqb = p["sections"][0]
    assert cqb["lead"].startswith("Content from TrueCombat: CQB") and len(cqb["items"]) == 5
    assert cqb["items"][0]["title"] == "Harbour"
    assert sum(len(s["items"]) for s in p["sections"]) == 41
    assert any("<location>" in it["text"] for it in p["sections"][4]["items"])      # entities decoded
    assert p["outro"][0].startswith("Thanks to GrooveSix")


def test_auto_plan_for_0380():
    b = B.plan(REL, SITE, "", SITE + "/release-0-38-0")
    assert b.version == "0.38.0" and b.changes == 41 and b.title == ""
    assert b.heading == "Our biggest update yet" and b.intro.startswith("Content from TrueCombat: CQB arrives")
    assert [h["title"] for h in b.headlines] == ["Experimental: TrueCombat: CQB comes to Platinum",
                                                 "Battlefield pickups", "Firing range", "Vaulting"]
    assert b.chips == ["Harbour", "Battlefield pickups", "Firing range", "Vaulting"]
    names = [n for n, _ in b.summaries]
    assert names[0] == "Also new" and "Experimental: TrueCombat: CQB comes to Platinum" not in names
    also = dict(b.summaries)["Also new"]
    assert "Know when to jump in" in also and "Battlefield pickups" not in also
    assert all(len(line) <= 200 for _, line in b.summaries)
    assert b.thanks.startswith("Thanks to GrooveSix")
    assert B.text_size(b) <= B.TEXT_BUDGET


def test_block_overrides_and_site_pictures(tmp_path):
    d = tmp_path / "img" / "releases" / "release-0-38-0"
    d.mkdir(parents=True)
    (d / "pickups.webp").write_bytes(b"x")
    (d / "2.jpg").write_bytes(b"x")
    (d / "hero.jpg").write_bytes(b"x")
    body = BODY + """
<!-- discord
title: Close Quarters
chips: Harbour | Pickups
headline: Battlefield pickups | Weapons drop when a player falls. Press Use to take one. | pickups.webp
headline: Firing range | Sight in every weapon from 10 to 100 metres.
headline: Vaulting | Over walls, crates and windows. | missing.webp
summary: Aim and Performance | Instant ADS zoom · Aim speed option
devlog: https://truecombat.eu/devlog/cqb
-->"""
    b = B.plan(dict(REL, body=body), SITE, str(tmp_path), SITE + "/release-0-38-0")
    assert b.title == "Close Quarters" and b.devlog_url.endswith("/devlog/cqb")
    assert b.chips == ["Harbour", "Pickups"]
    imgs = [h["image"] for h in b.headlines]
    assert imgs[0] == SITE + "/img/releases/release-0-38-0/pickups.webp"
    assert imgs[1] == SITE + "/img/releases/release-0-38-0/2.jpg"       # numbered fallback
    assert imgs[2] == ""                                                  # named file not on the site
    assert b.summaries == [("Aim and Performance", "Instant ADS zoom · Aim speed option")]
    assert b.art == d / "hero.jpg"
    assert "discord" not in B.parse(body)["outro"][-1]                    # the block never shows up as text


def test_layout_fits_discord_limits():
    b = B.plan(REL, SITE, "", SITE + "/release-0-38-0")
    b.headlines[1]["image"] = SITE + "/img/releases/release-0-38-0/1.webp"
    notify = discord.ui.Button(label="Notify me", custom_id="tcp:role:patchnotes")
    v = B.layout(b, "attachment://" + B.banner_name(b), "<@&5>", notify)
    comps = v.to_components()
    assert comps[0]["type"] == 10 and comps[0]["content"] == "<@&5>"
    container = comps[1]
    assert container["type"] == 17 and container["accent_color"] == B.ACCENT
    allc = list(walk(comps))
    assert len(allc) <= 40                                                # Discord's component cap
    assert sum(len(t) for t in texts(v)) <= 4000                          # Discord's text cap
    assert allc[2]["type"] == 12 and allc[2]["items"][0]["media"]["url"] == "attachment://patch-notes-0-38-0.jpg"
    assert any(c.get("type") == 9 and c["accessory"]["type"] == 11 for c in allc)   # section with thumbnail
    buttons = [c for c in allc if c.get("type") == 2]
    assert [x.get("label") for x in buttons] == ["Full patch notes", "Download", "Notify me"]
    assert buttons[0]["url"] == SITE + "/release-0-38-0"
    joined = "\n".join(texts(v))
    assert "## Our biggest update yet" in joined and "`v0.38.0` · 41 changes" in joined
    assert "### Everything else in 0.38.0" in joined


def test_layout_with_a_huge_release_stays_under_the_text_cap():
    items = "\n".join("- A long change line number %d that keeps on going about details, " % i + "x" * 160
                      for i in range(60))
    body = "**TRUECOMBAT: PLATINUM v9.9.9**\n\nShort intro. More.\n\n" + "\n\n".join(
        "**Section %d**\n%s" % (n, items) for n in range(12))
    b = B.plan({"tag_name": "v9.9.9", "body": body, "assets": []}, SITE, "", SITE)
    v = B.layout(b, SITE + "/img/og-news.jpg")
    assert sum(len(t) for t in texts(v)) <= 4000
    assert len(list(walk(v.to_components()))) <= 40


def test_short_labels():
    assert B.short({"title": "Vaulting", "text": "x"}) == "Vaulting"
    assert B.short({"title": "", "text": "Impacts react to what they hit: sparks on metal, splinters on wood."}) \
        == "Impacts react to what they hit"
    assert B.short({"title": "", "text": "New **Aim speed** option: keep the Classic feel."}) == \
        "New Aim speed option: keep the Classic feel"
    long = B.short({"title": "", "text": "Movement, stamina, recoil recovery and jumping now behave the same at "
                                         "every frame rate on every single machine."})
    assert long.endswith("…") and len(long) <= 66


def test_release_banner_renders():
    for title in ("Close Quarters", "", "A much longer update title that needs two lines or more"):
        data = cards.release_banner("0.38.0", title, ["Harbour", "Battlefield pickups"], None)
        im = Image.open(io.BytesIO(data))
        assert im.format == "JPEG" and im.size == (1600, 640)
