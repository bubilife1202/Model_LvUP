"""Score a results JSON produced by the experiment runner.

Usage:
  python3 score_runs.py <results.json>
  python3 score_runs.py --check <results.scored.json>

results.json: [{"task": ..., "arm": ..., "seed": ..., "answer": ..., ...}, ...]
Writes <results>.scored.json and prints a per-task/arm score table.
With --check, recomputes objective scores and verifies the stored scores
without writing a new file.
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKERS = os.path.join(HERE, "..", "bench", "checkers")
OBJECTIVE = {"T1_intervalset", "T2_ratewindow", "T3_M1_digits", "T3_M2_binary",
             "T4_constraints"}


def score_one(task, answer):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(answer)
        path = f.name
    try:
        out = subprocess.run(
            [sys.executable, os.path.join(CHECKERS, "score.py"), task, path],
            capture_output=True, text=True, timeout=120)
        return json.loads(out.stdout.strip())
    finally:
        os.unlink(path)


def main():
    check_only = len(sys.argv) > 2 and sys.argv[1] == "--check"
    src = sys.argv[2] if check_only else sys.argv[1]
    with open(src) as f:
        runs = json.load(f)

    mismatches = []
    for r in runs:
        if r["task"] in OBJECTIVE:
            s = score_one(r["task"], r["answer"])
            if check_only:
                expected = r.get("score")
                if expected is None or abs(expected - s["score"]) > 1e-12:
                    mismatches.append((r["task"], r["arm"], r["seed"], expected, s["score"]))
                continue
            r["score"] = s["score"]
            r["score_detail"] = s["detail"]

    if not check_only:
        out_path = src.replace(".json", ".scored.json")
        with open(out_path, "w") as f:
            json.dump(runs, f, indent=1)

    table = defaultdict(lambda: defaultdict(list))
    for r in runs:
        if "score" in r:
            table[r["task"]][r["arm"]].append(r["score"])

    arms = ["base-opus", "selfrefine", "bo3", "lvup", "base-fable"]
    print(f"\n{'task':<18}" + "".join(f"{a:>12}" for a in arms))
    for task in sorted(table):
        row = f"{task:<18}"
        for a in arms:
            v = table[task].get(a)
            row += f"{sum(v)/len(v):>12.3f}" if v else f"{'-':>12}"
        print(row)
    # macro average over tasks
    row = f"{'MACRO-AVG':<18}"
    for a in arms:
        per_task = [sum(v) / len(v) for t in sorted(table)
                    for v in [table[t].get(a)] if v]
        row += f"{sum(per_task)/len(per_task):>12.3f}" if per_task else f"{'-':>12}"
    print(row)
    if check_only:
        if mismatches:
            print("\nscore mismatches:")
            for task, arm, seed, expected, actual in mismatches:
                print(f"{task} {arm} seed={seed}: stored={expected} recomputed={actual}")
            raise SystemExit(1)
        print("\ncheck passed: stored objective scores match recomputation")
    else:
        print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
