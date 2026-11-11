"""Achievements: what they are and when a player has earned them.

Pure functions over the stats service's data, so the rules are easy to read
and test. The bot remembers what each player has unlocked (store.achievements).
"""

from __future__ import annotations

# key: (name, how it is earned, tier). Tier 3 is the rarest.
CAREER = {
    "first_match": ("Boots on the ground", "Finish your first ranked match", 1),
    "first_win": ("First blood", "Win a ranked match", 1),
    "matches_10": ("Regular", "Finish 10 ranked matches", 1),
    "matches_50": ("Veteran", "Finish 50 ranked matches", 2),
    "matches_100": ("Lifer", "Finish 100 ranked matches", 3),
    "wins_10": ("Winning habit", "Win 10 ranked matches", 1),
    "wins_50": ("Closer", "Win 50 ranked matches", 2),
    "wins_100": ("Unstoppable", "Win 100 ranked matches", 3),
    "kills_100": ("Rifleman", "100 kills", 1),
    "kills_500": ("Sharpshooter", "500 kills", 2),
    "kills_1000": ("Marksman", "1,000 kills", 2),
    "kills_5000": ("One-man army", "5,000 kills", 3),
    "headshots_100": ("Head hunter", "100 headshot kills", 2),
    "headshots_500": ("Surgeon", "500 headshot kills", 3),
    "rating_1100": ("On the rise", "Reach a skill rating of 1,100", 1),
    "rating_1250": ("Contender", "Reach a skill rating of 1,250", 2),
    "rating_1400": ("Elite", "Reach a skill rating of 1,400", 3),
    "streak_3": ("On a roll", "Win three ranked matches in a row", 1),
    "streak_5": ("Untouchable", "Win five ranked matches in a row", 3),
    "hours_10": ("Time served", "Play for 10 hours", 1),
    "hours_50": ("Home from home", "Play for 50 hours", 2),
}
MATCH = {
    "match_20": ("Wrecking crew", "20 kills in one match", 2),
    "match_30": ("Rampage", "30 kills in one match", 3),
    "match_hs10": ("Dead centre", "10 headshot kills in one match", 2),
    "match_survivor": ("Ghost", "Win a match with 10 or more kills and at most two deaths", 3),
    "match_mvp": ("Most valuable", "Top the scoreboard of a match you won", 1),
    "match_objective": ("Mission first", "Three objectives in one match", 2),
}
ALL = {**CAREER, **MATCH}
SEASON_KEY = "season_champion"
ALL[SEASON_KEY] = ("Season champion", "Finish a season in first place", 3)
TIER_MARK = {1: "▫️", 2: "🔹", 3: "🔶"}


def _steps(prefix: str, value, steps) -> list[str]:
    return ["%s_%d" % (prefix, s) for s in steps if (value or 0) >= s]


def career(p: dict) -> list[str]:
    """Everything a player's profile (tcp-player/1) has earned."""
    out = []
    matches, wins = p.get("matches") or 0, p.get("wins") or 0
    if matches:
        out.append("first_match")
    if wins:
        out.append("first_win")
    out += _steps("matches", matches, (10, 50, 100))
    out += _steps("wins", wins, (10, 50, 100))
    out += _steps("kills", p.get("kills"), (100, 500, 1000, 5000))
    out += _steps("headshots", p.get("headshots"), (100, 500))
    out += _steps("rating", max(p.get("rating") or 0, p.get("peakRating") or 0), (1100, 1250, 1400))
    out += _steps("hours", (p.get("timePlayed") or 0) / 3600, (10, 50))
    streak = 0
    for m in p.get("recent") or []:      # newest first
        if not m.get("won"):
            break
        streak += 1
    out += _steps("streak", streak, (3, 5))
    return out


def in_match(row: dict, scoreboard: list[dict]) -> list[str]:
    """What one scoreboard row (tcp-match-result/1 player) earned in that match."""
    out = []
    kills = row.get("kills") or 0
    out += _steps("match", kills, (20, 30))
    if (row.get("headshots") or 0) >= 10:
        out.append("match_hs10")
    if row.get("won") and kills >= 10 and (row.get("deaths") or 0) <= 2:
        out.append("match_survivor")
    if (row.get("objectives") or 0) >= 3:
        out.append("match_objective")
    if row.get("won") and scoreboard and len(scoreboard) >= 4:
        best = max(scoreboard, key=lambda r: (r.get("xp") or 0, r.get("kills") or 0))
        if best is row or best.get("id") == row.get("id"):
            out.append("match_mvp")
    return out


def label(key: str) -> str:
    name, _how, tier = ALL[key]
    return "%s %s" % (TIER_MARK[tier], name)


def best_first(keys) -> list[str]:
    order = list(ALL)
    return sorted((k for k in keys if k in ALL), key=lambda k: (-ALL[k][2], order.index(k)))
