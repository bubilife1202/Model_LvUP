"""Generate hidden-test expectations for T1 from the reference implementation,
cross-checked against hand-derived expectations. Writes t1_cases.json."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reference_interval_set import IntervalSet

# Each case: ops = [["add"|"remove", lo, hi, lo_closed, hi_closed], ...]
# checks: ["canonical", None, expected] or ["contains", x, expected]
# expected values are HAND-DERIVED; the script asserts the reference agrees.
A, R = "add", "remove"
CASES = [
    {"name": "empty", "ops": [], "checks": [["canonical", None, "{}"]]},
    {"name": "closed", "ops": [[A, 1, 2, True, True]], "checks": [["canonical", None, "[1, 2]"]]},
    {"name": "open", "ops": [[A, 1, 2, False, False]], "checks": [["canonical", None, "(1, 2)"]]},
    {"name": "touch-open-open-no-merge", "ops": [[A, 1, 2, False, False], [A, 2, 3, False, False]],
     "checks": [["canonical", None, "(1, 2) u (2, 3)"], ["contains", 2, False]]},
    {"name": "touch-halfopen-merge", "ops": [[A, 1, 2, True, False], [A, 2, 3, True, True]],
     "checks": [["canonical", None, "[1, 3]"]]},
    {"name": "touch-closed-open-merge", "ops": [[A, 1, 2, True, True], [A, 2, 3, False, True]],
     "checks": [["canonical", None, "[1, 3]"]]},
    {"name": "point-fills-gap", "ops": [[A, 1, 2, True, False], [A, 2, 3, False, True], [A, 2, 2, True, True]],
     "checks": [["canonical", None, "[1, 3]"]]},
    {"name": "degenerate-noop", "ops": [[A, 2, 2, True, False]], "checks": [["canonical", None, "{}"]]},
    {"name": "point-alone", "ops": [[A, 2, 2, True, True]],
     "checks": [["canonical", None, "{2}"], ["contains", 2, True], ["contains", 2.1, False]]},
    {"name": "contains-boundaries", "ops": [[A, 1, 2, True, False]],
     "checks": [["contains", 1, True], ["contains", 2, False], ["contains", 1.5, True]]},
    {"name": "overlap-merge", "ops": [[A, 1, 5, True, True], [A, 3, 7, True, False]],
     "checks": [["canonical", None, "[1, 7)"]]},
    {"name": "nested", "ops": [[A, 1, 10, True, True], [A, 3, 4, False, False]],
     "checks": [["canonical", None, "[1, 10]"]]},
    {"name": "cascade", "ops": [[A, 1, 2, True, True], [A, 3, 4, True, True], [A, 5, 6, True, True], [A, 2, 5, True, True]],
     "checks": [["canonical", None, "[1, 6]"]]},
    {"name": "floats", "ops": [[A, 0.5, 2.5, True, True]],
     "checks": [["canonical", None, "[0.5, 2.5]"]]},
    {"name": "point-no-touch", "ops": [[A, 1, 2, False, False], [A, 3, 3, True, True]],
     "checks": [["canonical", None, "(1, 2) u {3}"]]},
    {"name": "point-extends-right", "ops": [[A, 1, 2, False, False], [A, 2, 2, True, True]],
     "checks": [["canonical", None, "(1, 2]"]]},
    {"name": "point-extends-left", "ops": [[A, 1, 1, True, True], [A, 1, 2, False, False]],
     "checks": [["canonical", None, "[1, 2)"]]},
    {"name": "idempotent", "ops": [[A, 1, 2, True, True], [A, 1, 2, True, True]],
     "checks": [["canonical", None, "[1, 2]"]]},
    {"name": "closedness-upgrade", "ops": [[A, 1, 2, False, False], [A, 1, 2, True, True]],
     "checks": [["canonical", None, "[1, 2]"]]},
    {"name": "chain-open-result", "ops": [[A, 0, 1, False, True], [A, 1, 2, False, False], [A, 2, 3, True, False]],
     "checks": [["canonical", None, "(0, 3)"]]},
    {"name": "sorted-output", "ops": [[A, 5, 6, True, True], [A, 1, 2, True, True]],
     "checks": [["canonical", None, "[1, 2] u [5, 6]"], ["contains", 3, False]]},
    {"name": "negative", "ops": [[A, -3, -1, True, True]],
     "checks": [["canonical", None, "[-3, -1]"], ["contains", -2, True]]},
    {"name": "absorb-touching-open", "ops": [[A, 1, 2, True, True], [A, 2, 3, False, False]],
     "checks": [["canonical", None, "[1, 3)"]]},
    {"name": "two-points-merge-bridge", "ops": [[A, 1, 1, True, True], [A, 2, 2, True, True], [A, 1, 2, False, False]],
     "checks": [["canonical", None, "[1, 2]"]]},
    {"name": "spanning-many", "ops": [[A, 0, 1, True, False], [A, 2, 3, True, False], [A, 4, 5, True, False], [A, 0.5, 4.5, False, False]],
     "checks": [["canonical", None, "[0, 5)"]]},
    # ---- remove() cases ----
    {"name": "rm-open-hole", "ops": [[A, 1, 5, True, True], [R, 2, 3, False, False]],
     "checks": [["canonical", None, "[1, 2] u [3, 5]"], ["contains", 2, True], ["contains", 2.5, False]]},
    {"name": "rm-closed-hole", "ops": [[A, 1, 5, True, True], [R, 2, 3, True, True]],
     "checks": [["canonical", None, "[1, 2) u (3, 5]"], ["contains", 2, False], ["contains", 3, False]]},
    {"name": "rm-point", "ops": [[A, 1, 5, True, True], [R, 2, 2, True, True]],
     "checks": [["canonical", None, "[1, 2) u (2, 5]"], ["contains", 2, False], ["contains", 1.999, True]]},
    {"name": "rm-degenerate-noop", "ops": [[A, 1, 5, True, True], [R, 2, 2, True, False]],
     "checks": [["canonical", None, "[1, 5]"]]},
    {"name": "rm-everything", "ops": [[A, 1, 3, True, True], [R, 1, 3, True, True]],
     "checks": [["canonical", None, "{}"]]},
    {"name": "rm-interior-leaves-endpoints", "ops": [[A, 1, 3, True, True], [R, 1, 3, False, False]],
     "checks": [["canonical", None, "{1} u {3}"]]},
    {"name": "rm-right-overhang", "ops": [[A, 1, 3, False, False], [R, 2, 4, True, True]],
     "checks": [["canonical", None, "(1, 2)"]]},
    {"name": "rm-left-touch-closed", "ops": [[A, 1, 3, True, True], [R, 0, 1, True, True]],
     "checks": [["canonical", None, "(1, 3]"]]},
    {"name": "rm-right-touch-halfopen", "ops": [[A, 1, 3, True, True], [R, 3, 4, True, False]],
     "checks": [["canonical", None, "[1, 3)"]]},
    {"name": "rm-across-two", "ops": [[A, 1, 2, True, True], [A, 4, 5, True, True], [R, 1.5, 4.5, True, True]],
     "checks": [["canonical", None, "[1, 1.5) u (4.5, 5]"]]},
    {"name": "rm-open-touch-no-effect", "ops": [[A, 1, 5, True, True], [R, 5, 6, False, False]],
     "checks": [["canonical", None, "[1, 5]"]]},
    {"name": "rm-closed-touch-shaves-point", "ops": [[A, 1, 5, True, True], [R, 5, 6, True, True]],
     "checks": [["canonical", None, "[1, 5)"]]},
    {"name": "rm-from-empty", "ops": [[R, 1, 2, True, True]],
     "checks": [["canonical", None, "{}"]]},
    {"name": "rm-then-readd", "ops": [[A, 1, 5, True, True], [R, 2, 3, True, True], [A, 2, 3, False, False]],
     "checks": [["canonical", None, "[1, 2) u (2, 3) u (3, 5]"]]},
    {"name": "rm-open-region-from-open", "ops": [[A, 1, 5, False, False], [R, 0, 1, False, True]],
     "checks": [["canonical", None, "(1, 5)"]]},
]


def main():
    for case in CASES:
        s = IntervalSet()
        for op, lo, hi, lc, hc in case["ops"]:
            getattr(s, op)(lo, hi, lc, hc)
        for kind, arg, expected in case["checks"]:
            got = s.canonical() if kind == "canonical" else s.contains(arg)
            assert got == expected, (
                f"case {case['name']}: {kind}({arg}) -> {got!r}, hand-derived {expected!r}"
            )
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "t1_cases.json")
    with open(out, "w") as f:
        json.dump(CASES, f, indent=1)
    print(f"all {len(CASES)} hand-derived expectations match reference; wrote {out}")


if __name__ == "__main__":
    main()
