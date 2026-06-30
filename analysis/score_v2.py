"""Score v2 runs against bench/v2 task checkers.

Usage: python3 score_v2.py <runs.json>
Each run: {task, arm, model, seed, answer, ...}. Writes <runs>.scored.json and
prints a (task x arm@model) mean table.
"""
import json
import os
import subprocess
import sys
import tempfile
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "bench", "v2", "tasks")


def score_one(task, answer):
    check = os.path.join(ROOT, task, "check.py")
    if not os.path.exists(check):
        return None  # judged task
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(answer)
        path = f.name
    try:
        out = subprocess.run([sys.executable, check, path],
                             capture_output=True, text=True, timeout=180)
        return json.loads(out.stdout.strip())
    except Exception as e:
        return {"score": 0.0, "detail": {"error": repr(e), "stderr": out.stderr[-300:] if 'out' in dir() else ""}}
    finally:
        os.unlink(path)


def main():
    src = sys.argv[1]
    with open(src) as f:
        runs = json.load(f)
    for r in runs:
        if r.get("answer") is None:
            r["excluded"] = "no answer (failed run)"
            continue
        s = score_one(r["task"], r["answer"])
        if s is not None:
            r["score"] = s.get("score", 0.0)
            r["score_detail"] = s.get("detail", {})
    out_path = src.replace(".json", ".scored.json")
    with open(out_path, "w") as f:
        json.dump(runs, f, indent=1)

    table = defaultdict(lambda: defaultdict(list))
    cols = []
    for r in runs:
        if "score" in r:
            key = f"{r['arm']}@{r['model']}"
            table[r["task"]][key].append(r["score"])
            if key not in cols:
                cols.append(key)
    print(f"{'task':<24}" + "".join(f"{c:>16}" for c in cols))
    for t in sorted(table):
        row = f"{t:<24}"
        for c in cols:
            v = table[t].get(c)
            row += f"{sum(v)/len(v):>16.3f}" if v else f"{'-':>16}"
        print(row)
    row = f"{'MACRO':<24}"
    for c in cols:
        per = [sum(v)/len(v) for t in table for v in [table[t].get(c)] if v]
        row += f"{sum(per)/len(per):>16.3f}" if per else f"{'-':>16}"
    print(row)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
