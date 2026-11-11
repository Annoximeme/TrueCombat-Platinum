"""Team ratings and single-elimination brackets. Pure functions."""

from __future__ import annotations

ROUND_NAMES = {1: "Final", 2: "Semi-finals", 4: "Quarter-finals", 8: "Round of 16", 16: "Round of 32"}


def elo(winner: float, loser: float, k: float = 32.0) -> tuple[float, float]:
    """New ratings after a match. An upset moves more points than an expected win."""
    expected = 1.0 / (1.0 + 10 ** ((loser - winner) / 400.0))
    delta = k * (1.0 - expected)
    return winner + delta, loser - delta


def seed_order(size: int) -> list[int]:
    """Seed numbers in bracket order, so 1 and 2 can only meet in the final: 8 -> 1 8 4 5 2 7 3 6."""
    order = [1]
    while len(order) < size:
        n = len(order) * 2
        order = [x for s in order for x in (s, n + 1 - s)]
    return order


def build(teams: list[int]) -> list[list[dict]]:
    """A bracket for teams listed best seed first. Top seeds get the byes."""
    if len(teams) < 2:
        raise ValueError("a bracket needs at least two teams")
    size = 2
    while size < len(teams):
        size *= 2
    slots = [teams[s - 1] if s <= len(teams) else None for s in seed_order(size)]
    rounds = [[{"a": slots[i], "b": slots[i + 1], "w": None, "live": False} for i in range(0, size, 2)]]
    while len(rounds[-1]) > 1:
        rounds.append([{"a": None, "b": None, "w": None, "live": False} for _ in range(len(rounds[-1]) // 2)])
    for i, m in enumerate(rounds[0]):
        if m["b"] is None:
            report(rounds, 0, i, m["a"])
    return rounds


def report(rounds: list[list[dict]], r: int, i: int, winner: int) -> int | None:
    """Record a result and move the winner on. Returns the champion once the final is decided."""
    m = rounds[r][i]
    if winner not in (m["a"], m["b"]):
        raise ValueError("that team isn't in this match")
    m["w"], m["live"] = winner, False
    if r + 1 == len(rounds):
        return winner
    rounds[r + 1][i // 2]["a" if i % 2 == 0 else "b"] = winner
    return None


def pending(rounds: list[list[dict]], team: int | None = None) -> list[tuple[int, int, dict]]:
    """Matches that can be played now: both teams known, no winner yet."""
    out = []
    for r, rnd in enumerate(rounds):
        for i, m in enumerate(rnd):
            if m["a"] and m["b"] and not m["w"] and (team is None or team in (m["a"], m["b"])):
                out.append((r, i, m))
    return out


def round_name(rounds: list[list[dict]], r: int) -> str:
    return ROUND_NAMES.get(len(rounds[r]), "Round %d" % (r + 1))
