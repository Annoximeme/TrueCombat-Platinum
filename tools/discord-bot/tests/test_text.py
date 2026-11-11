import datetime as dt

import pytest

from tcpbot import text as T

NOW = dt.datetime(2026, 11, 8, 18, 0, tzinfo=dt.timezone.utc)   # 19:00 in Brussels, a Sunday


def local(when):
    return when.astimezone(T.ZoneInfo("Europe/Brussels")).strftime("%Y-%m-%d %H:%M")


@pytest.mark.parametrize("text,expect", [
    ("2026-11-15 20:00", "2026-11-15 20:00"),
    ("15/11 20:00", "2026-11-15 20:00"),
    ("15-11-2026 20.30", "2026-11-15 20:30"),
    ("tomorrow 21:30", "2026-11-09 21:30"),
    ("today 20:00", "2026-11-08 20:00"),
    ("sat 20:00", "2026-11-14 20:00"),
    ("Saturday 20h00", "2026-11-14 20:00"),
    ("sun 20:00", "2026-11-08 20:00"),
    ("sun 18:00", "2026-11-15 18:00"),
    ("18:30", "2026-11-09 18:30"),
    ("in 90m", "2026-11-08 20:30"),
    ("in 2h", "2026-11-08 21:00"),
])
def test_parse_when(text, expect):
    assert local(T.parse_when(text, "Europe/Brussels", NOW)) == expect


@pytest.mark.parametrize("text", ["", "yesterday 20:00", "2026-11-01 20:00", "today 18:00", "31/02 20:00",
                                  "25:00", "2027-12-01 20:00", "whenever"])
def test_parse_when_rejects(text):
    with pytest.raises(T.TimeError):
        T.parse_when(text, "Europe/Brussels", NOW)


BODY = """**TRUECOMBAT: PLATINUM — v0.33.0**
**Patch Notes #54**
**Packaged Native Sandbox** 0.33.0-sandbox24

Our biggest visual update yet. Ledge climbing returns.

**ULTRA VISUALS (DIRECTX 12)**
- New Ultra graphics preset in the launcher.
- Real-time sun shadows.

**MOVEMENT**
- Ledge climbing returns.

**DEVELOPMENT**
- Developed by RaziC* — Team Terminus.
"""


def test_parse_release_body():
    p = T.parse_release_body(BODY)
    assert p["header"][0].startswith("TRUECOMBAT")
    assert len(p["header"]) == 3
    assert p["intro"].startswith("Our biggest visual update yet.")
    assert [s["title"] for s in p["sections"]] == ["ULTRA VISUALS (DIRECTX 12)", "MOVEMENT", "DEVELOPMENT"]
    assert p["sections"][0]["items"] == ["New Ultra graphics preset in the launcher.", "Real-time sun shadows."]


def test_parse_release_body_without_intro():
    p = T.parse_release_body("**FIXES**\n- One\n- Two")
    assert p["sections"] == [{"title": "FIXES", "items": ["One", "Two"]}]


def test_split_notes_markers_and_limits():
    text = "part one\n\n----- NEXT DISCORD MESSAGE -----\n\npart two"
    assert T.split_notes(text) == ["part one", "part two"]
    long = "\n\n".join("**SECTION %d**\n" % i + "\n".join("- item %d" % j for j in range(30)) for i in range(6))
    parts = T.split_notes(long)
    assert all(len(p) <= 2000 for p in parts)
    assert "".join(parts).replace("\n", "") == long.replace("\n", "")
    one_line = "x" * 4500
    assert [len(p) for p in T.split_notes(one_line)] == [2000, 2000, 500]


def test_names_are_cleaned_and_escaped():
    assert T.clean("^1Red^7Fox") == "RedFox"
    assert T.md("*bold* @everyone") == "\\*bold\\* @​everyone"
    assert T.map_label("obj_snow") == "Snow"
    assert T.map_label("ctf_frost_bite") == "Frost Bite"
    assert T.map_image("https://truecombat.eu", "obj_village").endswith("/img/maps/village-hd.webp")


def test_tiers_and_bars():
    assert T.tier_for_level(1) == "enlisted"
    assert T.tier_for_level(5) == "nco"
    assert T.tier_for_level(12) == "officer"
    assert T.tier_for_level(21) == "general"
    assert T.progress_bar(800, 500, 1500, 10) == "█" * 3 + "░" * 7
    assert T.table([("a", "1"), ("bbb", "22")], "lr") == "a     1\nbbb  22"
