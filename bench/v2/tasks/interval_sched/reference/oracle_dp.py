"""Dynamic-programming oracle for interval_sched."""

from bisect import bisect_right


def _key(state):
    return (-state["weight"], state["count"], tuple(state["starts"]), tuple(state["ids"]))


def _better(left, right):
    return _key(left) < _key(right)


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
    prev = []
    for index, item in enumerate(items):
        prev.append(bisect_right(ends, item["start"], 0, index))

    dp = [{"weight": 0, "count": 0, "starts": [], "ids": []}]
    for index, item in enumerate(items, start=1):
        best_without = dp[index - 1]
        base = dp[prev[index - 1]]
        with_item = {
            "weight": base["weight"] + item["weight"],
            "count": base["count"] + 1,
            "starts": base["starts"] + [item["start"]],
            "ids": base["ids"] + [item["id"]],
        }
        dp.append(with_item if _better(with_item, best_without) else best_without)

    best = dp[-1]
    return best["weight"], list(best["ids"])
