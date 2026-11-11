import hashlib
import json
import time

from tcpbot.cogs.linking import player_id, read_request
from tcpbot.store import Store


def test_player_id_matches_stats_service():
    guid = "0123456789abcdef0123456789ABCDEF"
    # tools/server-bridge/tcp_stats.py: player_id(guid.upper()) = sha256("tcp-lb:" + raw)[:16]
    want = hashlib.sha256(("tcp-lb:" + guid.upper()).encode()).hexdigest()[:16]
    assert player_id(guid) == want
    assert player_id(guid.lower()) == want


def test_read_request(tmp_path):
    p = tmp_path / "ABC234.json"
    p.write_text(json.dumps({"code": "abc234", "guid": "A" * 32, "name": "^1Gianni"}))
    req = read_request(p)
    assert req == {"code": "ABC234", "pid": player_id("A" * 32), "name": "Gianni"}
    p.write_text(json.dumps({"code": "ABC234", "guid": "not-a-guid"}))
    assert read_request(p) is None
    p.write_text("garbage")
    assert read_request(p) is None


def test_link_codes_and_links():
    s = Store()
    code = s.new_link_code(42, minutes=15)
    assert len(code) == 6 and not set(code) & set("01OIL")
    again = s.new_link_code(42)            # a new code replaces the old one
    assert s.redeem_link_code(code) is None
    assert s.redeem_link_code(again.lower()) == 42
    assert s.redeem_link_code(again) is None   # single use
    assert s.link(42, "aaaaaaaaaaaaaaaa", "Gianni") is None
    assert s.link(43, "aaaaaaaaaaaaaaaa", "Gianni") == 42   # player moves to another account
    assert s.linked_player(42) is None
    assert s.linked_member("aaaaaaaaaaaaaaaa")["discord_id"] == 43
    assert s.unlink(43) and not s.unlink(43)


def test_expired_code():
    s = Store()
    code = s.new_link_code(7, minutes=0)
    s.db.execute("UPDATE link_codes SET expires=?", (int(time.time()) - 1,))
    assert s.redeem_link_code(code) is None


def test_rsvps_and_kv():
    s = Store()
    eid = s.add_event("event", "Scrims", "", int(time.time()) + 3600, 2, "", 1)
    s.rsvp(eid, 10, "going")
    s.rsvp(eid, 11, "maybe")
    s.rsvp(eid, 11, "going")
    s.rsvp(eid, 12, "waitlist")
    assert s.rsvps(eid) == {"going": [10, 11], "maybe": [], "waitlist": [12]}
    s.rsvp(eid, 10, None)
    assert s.rsvp_status(eid, 10) is None
    s.set("x", {"a": 1})
    assert s.get("x") == {"a": 1}
    assert [e["id"] for e in s.open_events()] == [eid]
