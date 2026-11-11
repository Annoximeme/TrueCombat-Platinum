"""Team balancing for pickup matches. Pure functions, covered by tests."""

from __future__ import annotations

import itertools
import random


def balance(ratings: dict[int, float], rng: random.Random | None = None) -> tuple[list[int], list[int]]:
    """Split players into two equal teams with the closest total rating.

    Tries every split (10 players = 126 distinct splits), so the result is the
    true optimum. Among equally good splits one is picked at random, so the same
    group doesn't always get the same teams.
    """
    rng = rng or random.Random()
    players = list(ratings)
    if len(players) % 2:
        raise ValueError("an even number of players is needed")
    half = len(players) // 2
    total = sum(ratings.values())
    best, options = None, []
    first = players[0]
    for combo in itertools.combinations(players[1:], half - 1):   # fix one player: skips mirrored splits
        red = (first,) + combo
        diff = abs(2 * sum(ratings[p] for p in red) - total)
        if best is None or diff < best - 1e-9:
            best, options = diff, [red]
        elif abs(diff - best) <= 1e-9:
            options.append(red)
    red = list(rng.choice(options))
    blue = [p for p in players if p not in red]
    if rng.random() < 0.5:
        red, blue = blue, red
    return sorted(red, key=lambda p: -ratings[p]), sorted(blue, key=lambda p: -ratings[p])


def fill_unrated(ratings: dict[int, float | None], default: float = 1000.0) -> dict[int, float]:
    """Players without a rating count as the average of the rated ones (or the default)."""
    known = [r for r in ratings.values() if r is not None]
    avg = sum(known) / len(known) if known else default
    return {p: (r if r is not None else avg) for p, r in ratings.items()}


def password(rng: random.Random | None = None) -> str:
    rng = rng or random.SystemRandom()
    words = ["alpha", "bravo", "delta", "echo", "foxtrot", "kilo", "lima", "oscar", "romeo", "sierra", "tango",
             "victor", "zulu", "hotel", "india", "mike"]
    return "%s%d" % (rng.choice(words), rng.randint(100, 999))
