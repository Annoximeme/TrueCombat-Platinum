"""Remote console for our own game servers, over UDP on the VPS itself.

The official and pickup servers only accept rcon from 127.0.0.1 traffic in
practice (ufw keeps the passwords off the internet anyway), and the passwords
reach the bot as systemd credentials (``LoadCredential=rcon-<key>:...``), never
through the config file.
"""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

PREFIX = b"\xff\xff\xff\xff"
COLOUR = re.compile(r"\^.")


class RconError(Exception):
    """The server did not answer, or the bot has no password for it."""


def password_for(server: dict) -> str:
    """rcon password for a server entry: credential file first, then an explicit path."""
    names = []
    cred_dir = os.environ.get("CREDENTIALS_DIRECTORY")
    if cred_dir and server.get("rcon_credential"):
        names.append(Path(cred_dir) / server["rcon_credential"])
    for key in ("rcon_password_file", "rcon_file"):
        if server.get(key):
            names.append(Path(server[key]))
    for p in names:
        try:
            text = p.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        # Accept a bare password or a cfg line such as: set rconpassword "secret"
        m = re.search(r'rconpassword\s+"?([^"\s]+)"?', text)
        pw = m.group(1) if m else text.splitlines()[0].strip() if text else ""
        if pw:
            return pw
    raise RconError("no rcon password configured for %s" % server.get("key", "server"))


def safe_arg(text: str, limit: int = 120) -> str:
    """Make free text safe inside one rcon command: no quotes, separators or colour codes."""
    text = COLOUR.sub("", str(text or ""))
    text = re.sub(r'[";\\\r\n\x00-\x1f]', " ", text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


class _Proto(asyncio.DatagramProtocol):
    def __init__(self):
        self.chunks: list[bytes] = []
        self.event = asyncio.Event()

    def datagram_received(self, data, addr):
        self.chunks.append(data)
        self.event.set()

    def error_received(self, exc):
        self.event.set()


async def rcon(host: str, port: int, password: str, command: str, timeout: float = 1.5,
               settle: float = 0.25) -> str:
    """Sends one command and returns the console text it printed (colour codes removed).
    Long answers arrive as several packets; collect until the line goes quiet."""
    loop = asyncio.get_running_loop()
    transport, proto = await loop.create_datagram_endpoint(_Proto, remote_addr=(host, int(port)))
    try:
        transport.sendto(PREFIX + ("rcon %s %s" % (password, command)).encode("latin-1", "replace"))
        try:
            await asyncio.wait_for(proto.event.wait(), timeout)
        except asyncio.TimeoutError as e:
            raise RconError("no answer from %s:%s" % (host, port)) from e
        while True:
            proto.event.clear()
            try:
                await asyncio.wait_for(proto.event.wait(), settle)
            except asyncio.TimeoutError:
                break
    finally:
        transport.close()
    out = []
    for data in proto.chunks:
        if data.startswith(PREFIX + b"print\n"):
            out.append(data[len(PREFIX) + 6:].decode("latin-1"))
    text = COLOUR.sub("", "".join(out))
    if "Bad rconpassword" in text or "rcon is locked" in text.lower():
        raise RconError("the server refused the rcon password")
    return text


async def server_rcon(server: dict, command: str, **kw) -> str:
    return await rcon(server["host"], server["port"], password_for(server), command, **kw)


# ---------------------------------------------------------------- parsers
STATUS_LINE = re.compile(r"^\s*(\d+)\s+(-?\d+)\s+(\d+|CNCT|ZMBI)\s+(.*?)\s+(\d+)\s+(\S+)\s+(\d+)\s+(\d+)(?:\s+\d+)?\s*$")


def parse_status(text: str) -> dict:
    """Engine 'status' output: map plus one row per slot (num score ping name lastmsg address qport rate)."""
    out = {"map": "", "players": []}
    for line in text.splitlines():
        if re.match(r"^map\s*:", line, re.I):
            out["map"] = line.split(":", 1)[1].strip()
            continue
        m = STATUS_LINE.match(line)
        if m:
            addr = m.group(6)
            out["players"].append({
                "slot": int(m.group(1)), "score": int(m.group(2)),
                "ping": -1 if not m.group(3).isdigit() else int(m.group(3)),
                "name": m.group(4).strip(), "address": addr,
                "bot": addr.lower() == "bot",
            })
    return out


BAN_LINE = re.compile(r"^#(\d+)\s+ip\s+(\S+)\s+guid\s+(\S+)\s+name\s+'(.*?)'\s+added\s+(\S+(?: \S+)?)(.*)$")


def parse_banlist(text: str) -> list[dict]:
    bans = []
    for line in text.splitlines():
        m = BAN_LINE.match(line.strip())
        if not m:
            continue
        rest = m.group(6)
        left = re.search(r"\((\d+) min left\)", rest)
        reason = re.search(r"reason:\s*(.*)$", rest)
        puid = re.search(r"\bpuid (\S+)", rest)
        bans.append({
            "number": int(m.group(1)),
            "ip": "" if m.group(2) == "-" else m.group(2),
            "guid": "" if m.group(3) == "-" else m.group(3),
            "name": m.group(4), "added": m.group(5).strip(),
            "minutes_left": int(left.group(1)) if left else 0,
            "reason": reason.group(1).strip() if reason else "",
            "puid": puid.group(1) if puid else "",
        })
    return bans
