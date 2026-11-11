"""Image cards and emoji art: they must always draw, whatever the data looks like."""

import io

from PIL import Image

from tcpbot import cards

from test_embeds import stats  # noqa: F401  (fixture)

PNG = b"\x89PNG\r\n\x1a\n"


def size(data):
    return Image.open(io.BytesIO(data)).size


def test_cards_draw_with_real_and_empty_data(stats, tmp_path):
    board = stats.leaderboard()
    p = stats.player(board["players"][0]["id"])
    for data in (cards.profile_card(p, str(tmp_path)), cards.leaderboard_card(board),
                 cards.leaderboard_card({"players": []}, "kd", "30d")):
        assert data[:8] == PNG and size(data)[0] == 1200
    bare = dict(p, weapons=[], recent=[], position=None, name="^1" + "W" * 60)
    assert size(cards.profile_card(bare)) == (1200, 630)
    row = stats.recent()["matches"][0]
    assert cards.match_card(row, stats.match(row["id"]))[:8] == PNG
    assert cards.match_card(row, None)[:8] == PNG
    assert size(cards.banner()) == (1500, 600)


def test_icons_fit_discord_limits():
    icons = cards.icon_set()
    assert {"tcp_rank02", "tcp_rank11", "tcp_specops", "tcp_terrorists", "tcp_live", "tcp_medal1"} <= set(icons)
    for name, img in icons.items():
        assert 2 <= len(name) <= 32 and name.replace("_", "").isalnum()
        assert img.size == (128, 128)
        assert len(cards.png(img)) < 256 * 1024


def test_insignia_follow_the_level_ladder():
    assert cards.insignia_key(1) == "rank02" and cards.insignia_key(5) == "rank03"
    assert cards.insignia_key(14) == "rank06" and cards.insignia_key(21) == "rank11"
    assert cards.insignia_key(99) == "rank11" and cards.insignia_key(0) == "rank02"
    assert len(cards.INSIGNIA) == 21
