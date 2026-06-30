"""Generate frozen hidden expectations for interval_sched."""

import json
import os

from oracle_bruteforce import solve as solve_bruteforce
from oracle_dp import solve as solve_dp


CASES = [
    {"name": "empty", "intervals": []},
    {"name": "single_positive", "intervals": [["a", 1, 4, 9]]},
    {"name": "single_negative_prefers_empty", "intervals": [["a", 1, 4, -3]]},
    {"name": "touching_chain", "intervals": [["a", 1, 3, 4], ["b", 3, 5, 6], ["c", 5, 8, 7]]},
    {"name": "strict_overlap", "intervals": [["a", 1, 4, 7], ["b", 3, 6, 8], ["c", 5, 9, 9]]},
    {"name": "all_overlapping_weight_tie_start_break", "intervals": [["a", 1, 5, 10], ["b", 2, 6, 10], ["c", 3, 7, 10]]},
    {"name": "weight_tie_fewer_intervals", "intervals": [["a", 1, 4, 10], ["b", 1, 2, 5], ["c", 2, 4, 5]]},
    {"name": "weight_and_count_tie_start_list_break", "intervals": [["a", 1, 4, 5], ["b", 4, 6, 5], ["c", 2, 3, 5], ["d", 3, 6, 5]]},
    {"name": "final_id_tie_break", "intervals": [["b", 1, 3, 5], ["a", 1, 3, 5], ["c", 4, 5, 1]]},
    {"name": "zero_length_with_regular", "intervals": [["a", 1, 3, 5], ["b", 3, 3, 2], ["c", 3, 5, 6]]},
    {"name": "multiple_zero_length_same_time", "intervals": [["a", 2, 2, 3], ["b", 2, 2, 4], ["c", 2, 2, -1], ["d", 1, 2, 5], ["e", 2, 4, 6]]},
    {"name": "zero_length_bridge_with_negative_option", "intervals": [["a", 0, 0, 2], ["b", 0, 3, 5], ["c", 3, 3, 2], ["d", 3, 6, 5], ["e", 0, 6, 12]]},
    {"name": "same_end_choose_chain", "intervals": [["a", 1, 5, 8], ["b", 1, 3, 4], ["c", 3, 5, 4], ["d", 5, 7, 1]]},
    {"name": "same_start_different_end", "intervals": [["a", 1, 4, 6], ["b", 1, 2, 3], ["c", 2, 4, 3], ["d", 4, 6, 5]]},
    {"name": "input_unsorted", "intervals": [["d", 6, 7, 4], ["a", 1, 3, 4], ["c", 3, 6, 6], ["b", 0, 1, 1]]},
    {"name": "all_zero_weight_prefers_empty", "intervals": [["a", 1, 2, 0], ["b", 2, 3, 0], ["c", 5, 5, 0]]},
    {"name": "touching_vs_longer", "intervals": [["a", 0, 2, 5], ["b", 2, 4, 5], ["c", 0, 4, 10], ["d", 4, 4, 1]]},
    {"name": "nested_and_zero_length", "intervals": [["a", 1, 8, 11], ["b", 2, 2, 3], ["c", 2, 5, 4], ["d", 5, 5, 3], ["e", 5, 8, 4]]},
    {"name": "negative_inside_best_chain", "intervals": [["a", 1, 3, 5], ["b", 3, 4, -2], ["c", 4, 6, 5], ["d", 1, 6, 9]]},
    {"name": "all_overlapping_final_id", "intervals": [["c", 4, 9, 7], ["a", 4, 9, 7], ["b", 4, 9, 7]]},
    {"name": "same_start_list_but_id_break", "intervals": [["x", 0, 2, 3], ["y", 0, 2, 3], ["a", 2, 4, 3], ["b", 2, 4, 3]]},
    {"name": "repeated_touching_zero_length", "intervals": [["a", 1, 1, 1], ["b", 1, 2, 2], ["c", 2, 2, 1], ["d", 2, 3, 2], ["e", 3, 3, 1]]},
    {"name": "many_equal_ends", "intervals": [["a", 1, 4, 5], ["b", 2, 4, 5], ["c", 0, 1, 1], ["d", 4, 6, 4], ["e", 4, 6, 4]]},
    {"name": "all_overlapping_negative_and_zero", "intervals": [["a", 1, 5, -2], ["b", 1, 5, 0], ["c", 1, 5, -1]]},
    {"name": "long_chain_with_decoy", "intervals": [["a", 0, 2, 3], ["b", 2, 5, 7], ["c", 5, 7, 4], ["d", 0, 7, 13], ["e", 7, 9, 2]]},
    {"name": "equal_weight_choose_earlier_starts", "intervals": [["a", 1, 2, 4], ["b", 2, 5, 6], ["c", 3, 4, 4], ["d", 4, 5, 6]]},
    {
        "name": "stress_non_overlapping_chain",
        "intervals": [[f"n{index:02d}", index * 2, index * 2 + 1, index + 1] for index in range(30)],
    },
    {
        "name": "stress_zero_weight_chain",
        "intervals": [[f"z{index:02d}", index * 2, index * 2 + 1, 0] for index in range(30)],
    },
]


def _chosen_starts(intervals, chosen_ids):
    lookup = {interval_id: (start, end) for interval_id, start, end, _ in intervals}
    ordered = sorted(
        [(interval_id, lookup[interval_id][0], lookup[interval_id][1]) for interval_id in chosen_ids],
        key=lambda item: (item[2], item[1], item[0]),
    )
    return [item[1] for item in ordered]


def main():
    frozen = []
    for case in CASES:
        intervals = [tuple(entry) for entry in case["intervals"]]
        expected_dp = solve_dp(intervals)
        expected_bruteforce = solve_bruteforce(intervals)
        assert expected_dp == expected_bruteforce, (
            "oracle mismatch for %s: %r != %r" % (case["name"], expected_dp, expected_bruteforce)
        )
        total_weight, chosen_ids = expected_dp
        frozen.append(
            {
                "name": case["name"],
                "intervals": case["intervals"],
                "expected_weight": total_weight,
                "expected_ids": chosen_ids,
                "expected_starts": _chosen_starts(intervals, chosen_ids),
            }
        )
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "hidden_tests.json")
    with open(out_path, "w") as handle:
        json.dump({"tests": frozen}, handle, indent=2, sort_keys=True)
    print("wrote %d frozen cases to %s" % (len(frozen), out_path))


if __name__ == "__main__":
    main()
