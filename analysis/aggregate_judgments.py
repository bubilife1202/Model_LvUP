"""Aggregate pairwise verdicts from all judges into per-pair win tables.

Usage: python3 aggregate_judgments.py results/judging
Reads manifest.json, gpt55_judge_verdicts.jsonl, gemini_verdicts.jsonl,
claude_verdicts.json. Prints per-task, per-pair outcomes by judge family
and combined.
"""
import json
import os
import sys
from collections import defaultdict


def main():
    d = sys.argv[1]
    manifest = {m["id"]: m for m in json.load(open(f"{d}/manifest.json"))}
    verdicts = []
    for f in ("gpt55_judge_verdicts.jsonl", "gemini_verdicts.jsonl"):
        p = os.path.join(d, f)
        if os.path.exists(p):
            for line in open(p):
                if line.strip():
                    verdicts.append(json.loads(line))
    p = os.path.join(d, "claude_verdicts.json")
    if os.path.exists(p):
        verdicts.extend(json.load(open(p)))

    # per (task, pair, judge): count wins by arm
    table = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    for v in verdicts:
        if v["verdict"] is None:
            continue
        m = manifest[v["id"]]
        key = (m["task"], tuple(m["pair"]))
        jf = v["judge"].split("-")[0].replace("claude", "claude")
        if v["verdict"] == "A":
            winner = m["A"]
        elif v["verdict"] == "B":
            winner = m["B"]
        else:
            winner = "TIE"
        table[key][(v["judge"], winner)] += 1
        counts[key] += 1

    for key in sorted(table):
        task, pair = key
        print(f"\n{task}  {pair[0]} vs {pair[1]}  (n={counts[key]})")
        judges = sorted({j for (j, w) in table[key]})
        for j in judges:
            row = {w: table[key][(jj, w)] for (jj, w) in table[key] if jj == j}
            print(f"  {j:14s} " + "  ".join(f"{w}:{int(c)}" for w, c in sorted(row.items())))
        # combined
        comb = defaultdict(int)
        for (j, w), c in table[key].items():
            comb[w] += c
        total = sum(comb.values())
        print("  COMBINED       " + "  ".join(
            f"{w}:{int(c)} ({c/total:.0%})" for w, c in sorted(comb.items())))


if __name__ == "__main__":
    main()
