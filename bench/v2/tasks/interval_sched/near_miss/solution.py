"""Plausible but flawed solution for interval_sched.

Bugs:
- Uses strict `<` compatibility, so touching and same-time zero-length cases fail.
- Breaks remaining ties by id list only, ignoring the required start-time list.
"""

from bisect import bisect_left


def _key(state):
    return (-state[0], state[1], state[2])


def weighted_interval_schedule(intervals):
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
    prev = []
    for index, item in enumerate(items):
        prev.append(bisect_left(ends, item["start"], 0, index))

    states = [(0, 0, ())]
    for index, item in enumerate(items, start=1):
        without_item = states[index - 1]
        base = states[prev[index - 1]]
        with_item = (
            base[0] + item["weight"],
            base[1] + 1,
            base[2] + (item["id"],),
        )
        states.append(with_item if _key(with_item) < _key(without_item) else without_item)

    best = states[-1]
    return best[0], list(best[2])
