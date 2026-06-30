"""Alternate memoized oracle for interval_sched."""

from bisect import bisect_right
from functools import lru_cache


def _key(state):
    return (-state[0], state[1], state[2], state[3])


def solve(intervals):
    items = [
        {
            "id": interval_id,
            "start": start,
            "end": end,
            "weight": weight,
        }
        for interval_id, start, end, weight in intervals
    ]
    items.sort(key=lambda item: (item["end"], item["start"], item["id"]))
    ends = [item["end"] for item in items]
    prev = [bisect_right(ends, item["start"], 0, index) for index, item in enumerate(items)]

    @lru_cache(maxsize=None)
    def solve_prefix(length):
        if length == 0:
            return (0, 0, (), ())

        without_item = solve_prefix(length - 1)
        item = items[length - 1]
        base = solve_prefix(prev[length - 1])
        with_item = (
            base[0] + item["weight"],
            base[1] + 1,
            base[2] + (item["start"],),
            base[3] + (item["id"],),
        )
        return with_item if _key(with_item) < _key(without_item) else without_item

    best = solve_prefix(len(items))
    return best[0], list(best[3])
