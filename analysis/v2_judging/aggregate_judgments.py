"""Aggregate v2 pairwise judge verdicts.

Usage:
    python3 analysis/v2_judging/aggregate_judgments.py [results/v2/judging]
"""
import json
import os
import sys
from collections import defaultdict


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def dedupe_first(rows):
    seen = set()
    deduped = []
    for row in rows:
        key = (row.get("id"), row.get("judge"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def main(argv):
    directory = argv[1] if len(argv) > 1 else os.path.join("results", "v2", "judging")
    manifest_path = os.path.join(directory, "manifest.json")
    manifest = {row["id"]: row for row in json.load(open(manifest_path))}

    verdicts = []
    verdicts.extend(load_jsonl(os.path.join(directory, "gpt55_judge_verdicts.jsonl")))
    verdicts.extend(load_jsonl(os.path.join(directory, "gemini_verdicts.jsonl")))
    verdicts = dedupe_first(verdicts)

    table = defaultdict(lambda: defaultdict(int))
    counts = defaultdict(int)
    for verdict in verdicts:
        outcome = verdict.get("verdict")
        if outcome is None:
            continue
        meta = manifest.get(verdict.get("id"))
        if not meta:
            continue
        key = (meta["task"], tuple(meta["pair"]))
        if outcome == "A":
            winner = meta["A"]
        elif outcome == "B":
            winner = meta["B"]
        else:
            winner = "TIE"
        table[key][(verdict["judge"], winner)] += 1
        counts[key] += 1

    for key in sorted(table):
        task, pair = key
        print("\n%s  %s vs %s  (n=%d)" % (task, pair[0], pair[1], counts[key]))
        judges = sorted({judge for judge, _ in table[key]})
        for judge in judges:
            row = {}
            for (current_judge, winner), count in table[key].items():
                if current_judge == judge:
                    row[winner] = count
            cells = ["%s:%d" % (winner, row[winner]) for winner in sorted(row)]
            print("  %-14s %s" % (judge, "  ".join(cells)))
        combined = defaultdict(int)
        for (_, winner), count in table[key].items():
            combined[winner] += count
        total = sum(combined.values())
        cells = []
        for winner in sorted(combined):
            count = combined[winner]
            cells.append("%s:%d (%.0f%%)" % (winner, count, 100.0 * count / total))
        print("  COMBINED       " + "  ".join(cells))


if __name__ == "__main__":
    main(sys.argv)
