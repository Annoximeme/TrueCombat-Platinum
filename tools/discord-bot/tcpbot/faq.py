"""The answers behind /ask.

Curated by hand from the website's questions page and guide, plus how things
work on this Discord. No language model: a question is matched on its words,
so an answer is always one the team wrote. Keep entries short and current;
{site} and {invite} are filled in from the config.
"""

from __future__ import annotations

import math
import re

# (question, answer, extra words that should also find it, page on the site)
ENTRIES = [
    ("What is TrueCombat: Platinum?",
     "A native 64-bit Windows rebuild of TrueCombat: Elite, the realistic modern-combat total conversion for Enemy "
     "Territory. It has a DirectX 12 renderer, the original maps, soldiers and HUD, and a launcher that hosts servers "
     "and installs signed updates.", "about game tce elite remake", "/faq.html"),
    ("Is it free?",
     "Yes. There is no store and nothing to unlock with money, and every weapon is available from your first match.",
     "cost price pay buy money unlock", "/faq.html"),
    ("Do I need TrueCombat: Elite or Enemy Territory installed?",
     "No. The download contains everything needed to play.", "require original wolfenstein et install", "/faq.html"),
    ("What do I need to run it?",
     "Windows 10 or 11, 64-bit, a DirectX 12 graphics card and about 2.3 GB of free disk space. Older cards can use "
     "**Safe start**, which runs the game on OpenGL.", "requirements specs system pc hardware gpu minimum", "/faq.html"),
    ("How do I install it?",
     "Download the installer from the download page, choose a folder and let the launcher fetch the game. After that "
     "the launcher keeps the game and itself up to date.", "download setup installer get launcher", "/download.html"),
    ("How do I update the game?",
     "Start the launcher. It checks for a new version every time, downloads only what changed and verifies the update's "
     "signature before installing it.", "update patch new version latest upgrade", "/news.html"),
    ("I'm new. Where do I start?",
     "Read the beginner's guide for the controls, game modes and a few tips that keep you alive longer. The weapons "
     "page lists every gun, and the maps page has an overhead layout of every map.",
     "beginner newbie learn controls tutorial tips guide how play", "/guide.html"),
    ("Can I play online? Which servers are there?",
     "Yes. Two official EU servers run around the clock: **Official #1** is ranked, and **Official #2** is unranked "
     "with bots filling the empty slots. Both are in the launcher's Servers tab next to every other public server, and "
     "`/servers` shows who is on right now.", "multiplayer server official join connect ip address", "/servers.html"),
    ("Can I host my own server?",
     "Yes. Press **Host a server** in the launcher and pick the mode, map rotation and player limit. Switch on "
     "**List publicly** to appear on the server list. Players outside your home network need UDP port 27971 forwarded "
     "to the hosting PC.", "host dedicated own private port forward lan", "/faq.html"),
    ("How do the leaderboards and ranks work?",
     "Every completed match on a ranked server counts. You earn XP for kills, headshots, rounds won, objectives and "
     "finishing matches, and XP moves you up the ranks. Your skill rating goes up when you win and down when you lose, "
     "by more when the result was a surprise. You appear on the board after your first completed match. `/profile` "
     "and `/top` show it here.", "leaderboard rank ranking rating elo xp experience level points stats", "/leaderboards.html"),
    ("How is XP calculated?",
     "10 per kill, 5 more for a headshot kill, 20 per round won, 30 per objective, 100 for a match win (25 otherwise) "
     "and 2 per minute played. A team kill costs 25.", "xp experience points formula earn score", "/leaderboards.html"),
    ("Why am I not on the leaderboard?",
     "Only completed matches on a **ranked** server count, so leaving early or playing on the unranked server doesn't "
     "put you on the board. Official #1 is the ranked one. A ranked match ends after 10 rounds or 20 minutes.",
     "missing leaderboard unranked not showing profile stats empty", "/leaderboards.html"),
    ("How do I link my Discord account to my game profile?",
     "Use `/link` here to get a one-time code, then type `/link CODE` in the game console (or `!link CODE` in chat) "
     "while you're on an official server. Discord confirms within seconds. No password and no sign-up: the key file on "
     "your PC stays your identity.", "link connect account verify verified role profile discord", ""),
    ("How do the seasons work?",
     "A season follows the calendar. Everyone starts from zero, and the XP you earn in ranked matches during the "
     "season is your season score. The winner gets the Season champion role until the next one. `/season` shows the "
     "standings.", "season reset champion monthly standings", ""),
    ("What are achievements?",
     "Milestones the bot hands out for what you do in ranked matches: first win, kill counts, win streaks, standout "
     "matches and more. `/achievements` shows yours and what to go for next.", "achievement badge milestone medal unlock", ""),
    ("How does the pickup queue work?",
     "Press **Join queue** in the pickup channel (or `/pickup join`). When two full teams are in, everyone gets a "
     "60-second ready check. The bot balances the teams on skill rating, sets up a private match server and sends you "
     "your team and a join line by DM.", "pickup pug queue match find game competitive mix", "/competitive.html"),
    ("Is there a mode for clan matches?",
     "Yes. Match mode adds ready-up, a knife round for sides, half-time and tactical timeouts that freeze the whole "
     "match. It is built into every server. On Discord, teams challenge each other with `/scrim challenge` and the bot "
     "sets the server up.", "clan war match mode competitive scrim knife timeout ready", "/competitive.html"),
    ("How do I create or join a team?",
     "`/team create` starts a team with you as captain, and `/team invite` adds players. A player accepts with the "
     "button in their DM or `/team join`. `/team list` is the team ladder; scrims and tournament matches move it.",
     "team clan create join invite roster captain ladder", ""),
    ("How do tournaments work?",
     "Staff open a tournament and captains sign their team up with the button on its card. The bracket is single "
     "elimination, seeded on team rating. When both teams are ready a captain starts the match with "
     "`/tournament play`, and the winner moves on automatically.", "tournament cup bracket sign up signup competition", ""),
    ("Can I play offline?",
     "Yes. **Practice offline with bots** in the launcher starts a match in one click, with no connection needed.",
     "offline bots singleplayer practice solo training", "/faq.html"),
    ("Where do I find players? When are people online?",
     "Right here. Take the **Match alerts** role with `/notify` to get a ping when a match is filling up, follow a "
     "friend with `/alerts player`, and keep an eye on the live server cards. Evenings in Europe are the busiest.",
     "players empty nobody online when active population find people", "/servers.html"),
    ("DirectX 12 won't start or the game crashes on launch. What now?",
     "Press **Safe start** in the launcher. It runs the game on OpenGL in a 1280 × 720 window, and the game also falls "
     "back to OpenGL by itself if DirectX 12 fails. If it still won't start, send a `/bug` report with your graphics "
     "card and Windows version.", "crash start launch black screen dx12 directx error won't open broken", "/faq.html"),
    ("Can I keep the original look?",
     "Yes. The **Low** preset is the original look, with stock filtering and no added effects. **High** is the "
     "default, and **Ultra** adds modern lighting and real-time sun shadows. You can switch at any time from the "
     "launcher.", "graphics preset original classic look low high ultra settings quality", "/faq.html"),
    ("Does it support DLSS?",
     "Yes. NVIDIA DLSS and DLAA are optional on RTX cards. Everything else runs on any DirectX 12 card.",
     "dlss dlaa nvidia rtx upscaling fsr", "/faq.html"),
    ("Does it support ultrawide monitors?",
     "Yes. The field of view widens on 21:9 and 32:9 screens instead of cropping, and the HUD stays centred.",
     "ultrawide widescreen 21:9 32:9 fov resolution monitor", "/faq.html"),
    ("Is there a Linux or Mac version?",
     "The dedicated server runs natively on Linux, and both official servers use it. The game itself is for Windows.",
     "linux mac macos steam deck proton", "/faq.html"),
    ("Is this complete TC:E?",
     "Very nearly. Every weapon, all seven game modes, the original movement speed, leaning, ladders and swimming are "
     "in. The roadmap shows what is playable now and what follows.", "complete finished missing features roadmap status", "/news.html"),
    ("Is it an official TrueCombat release? Who makes it?",
     "TrueCombat: Elite was created by Team Terminator. TrueCombat: Platinum is a fan project by Team Terminus, two "
     "TC:E veterans: RaziC* leads development and RavoC leads the community. It is not affiliated with or endorsed by "
     "the original team.", "official developer team who made author terminus terminator studio", "/studio.html"),
    ("How do I follow development? When is the next update?",
     "The devlog explains what is being built and why, the patch notes list every change, and new versions are "
     "announced here on Discord first. We don't promise dates: an update ships when it passes the full test run.",
     "devlog news update release date when next patch notes roadmap", "/devlog.html"),
    ("How can I support the project?",
     "Playing and bringing a friend helps most. If you want to chip in towards the servers, the support page shows "
     "where every euro goes. Nothing in the game is sold.", "donate donation support kofi ko-fi money help contribute", "/support.html"),
    ("How do I report a bug?",
     "Use `/bug` here. It asks what happened and how to make it happen again, and you get a DM when the team has "
     "looked at it. Screenshots and clips are welcome in chat afterwards.", "bug report issue problem glitch broken error", ""),
    ("How do I report a cheater or a player?",
     "Type `/report` in the game console while you're on the server with them. The report reaches staff with the "
     "match details attached. Please don't accuse players in public channels.", "cheater cheat hacker report player abuse aimbot wallhack toxic", ""),
    ("I was banned. Can I appeal?",
     "Yes. Use `/appeal` here and tell us what happened. Staff read every appeal and you get the answer by DM.",
     "ban banned appeal unban kicked", ""),
    ("How do I suggest a feature or a map?",
     "Use `/suggest`. Your idea goes up in the suggestions channel where everyone gets one vote, and the team marks "
     "what is planned. `/suggestion top` shows the most wanted.", "suggest suggestion idea feature request wish map vote", ""),
    ("I want to write about it or make a video",
     "Grab the press kit with logos, unedited screenshots and a fact sheet. Videos and streams are welcome, no "
     "permission needed.", "press media video stream youtube twitch article logo screenshots", "/press.html"),
]

STOP = set("a an and are as at be but by can do does for from have how i i'm if in is it it's me my of on or so that the "
           "there this to up was we what when where which who why will with you your not no get got work game".split())
WORD = re.compile(r"[a-z0-9][a-z0-9:+#'-]*")


def words(text: str) -> list[str]:
    out = []
    for w in WORD.findall((text or "").lower()):
        w = w.strip("'-")
        if w in STOP:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        if w and w not in STOP:
            out.append(w)
    return out


INDEX = [(set(words(q)), set(words(extra)), set(words(a))) for q, a, extra, _url in ENTRIES]
# A word found in many entries ("game", "server") says little; a rare one ("dlss") says a lot.
_SEEN: dict[str, int] = {}
for _t, _x, _b in INDEX:
    for _w in _t | _x | _b:
        _SEEN[_w] = _SEEN.get(_w, 0) + 1


def _weight(word: str) -> float:
    return math.log(1 + len(INDEX) / _SEEN.get(word, 1))


def search(question: str, limit: int = 3) -> list[tuple[int, float]]:
    """Entry indexes that answer a question, best first, with a score. Empty when nothing fits."""
    asked = set(words(question))
    if not asked:
        return []
    scored = []
    for i, (title, extra, body) in enumerate(INDEX):
        score, strong = 0.0, False
        for w in asked:
            if w in title or w in extra:
                score += _weight(w) * (1.0 if w in title else 0.9)
                strong = True
            elif w in body:
                score += _weight(w) * 0.3
            elif len(w) >= 5 and any(k.startswith(w[:5]) or w.startswith(k) and len(k) >= 5 for k in title | extra):
                score += 1.2                 # near-misses: "installing" finds "install"
                strong = True
        if strong and score >= 1.5:
            scored.append((i, score))
    scored.sort(key=lambda x: -x[1])
    return scored[:limit]
