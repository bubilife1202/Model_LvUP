"""Build a domain map from scored v2 runs.

Usage:
    python3 analysis/v2_domain_map.py <scored.json...>

Outputs:
    - results/v2/domain_map.json
    - docs/DOMAIN_MAP.md
"""
import json
import os
import sys
from collections import defaultdict


MODEL_ORDER = ["haiku", "sonnet", "opus", "fable"]
VERDICT_THRESHOLDS = [
    ("helps strongly", 0.10),
    ("helps", 0.03),
    ("neutral", -0.03),
]


def usage():
    raise SystemExit("usage: python3 analysis/v2_domain_map.py <scored.json...>")


def mean(values):
    return sum(values) / len(values) if values else None


def ordered_models(models):
    known = [model for model in MODEL_ORDER if model in models]
    extra = sorted(model for model in models if model not in MODEL_ORDER)
    return known + extra


def ensure_parent(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def load_runs(paths):
    runs = []
    for path in paths:
        with open(path) as handle:
            payload = json.load(handle)
        if not isinstance(payload, list):
            raise ValueError("%s is not a JSON list" % path)
        for run in payload:
            if not isinstance(run, dict):
                continue
            task = run.get("task", run.get("taskId"))
            arm = run.get("arm")
            model = run.get("model")
            score = run.get("score")
            if task is None or arm is None or model is None:
                continue
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                continue
            runs.append({
                "task": task,
                "arm": arm,
                "model": model,
                "score": float(score),
            })
    return runs


def load_task_meta():
    root = os.path.join("bench", "v2", "tasks")
    meta = {}
    for task_id in sorted(os.listdir(root)):
        path = os.path.join(root, task_id, "task.json")
        if not os.path.exists(path):
            continue
        with open(path) as handle:
            data = json.load(handle)
        meta[data["id"]] = {
            "category": data["category"],
            "verifiability": data["verifiability"],
        }
    return meta


def verdict_for(value):
    if value is None:
        return None
    for label, floor in VERDICT_THRESHOLDS:
        if value >= floor:
            return label
    return "avoid"


def reason_for(verdict, models, n_cells):
    measured = [(model, row["delta"]) for model, row in models.items() if row["delta"] is not None]
    if not measured:
        return "No numeric base/RAAR overlap was present in the supplied results."
    measured.sort(key=lambda item: item[1], reverse=True)
    best_model, best_value = measured[0]
    worst_model, worst_value = measured[-1]
    if verdict == "helps strongly":
        return "Largest measured gain is %.3f on %s across %d measured model cells." % (
            best_value, best_model, n_cells)
    if verdict == "helps":
        return "Measured gains are positive overall; strongest on %s at %.3f across %d measured model cells." % (
            best_model, best_value, n_cells)
    if verdict == "neutral":
        return "Effects are small or mixed; range spans %.3f on %s to %.3f on %s." % (
            worst_value, worst_model, best_value, best_model)
    return "Measured deltas are negative overall; weakest result is %.3f on %s." % (worst_value, worst_model)


def main(argv):
    if len(argv) < 2:
        usage()

    runs = load_runs(argv[1:])
    meta = load_task_meta()

    task_means = defaultdict(lambda: defaultdict(dict))
    models = set()
    for run in runs:
        task, arm, model = run["task"], run["arm"], run["model"]
        models.add(model)
        task_means[task][model].setdefault(arm, []).append(run["score"])

    task_level = {}
    for task, per_model in task_means.items():
        task_level[task] = {}
        for model, per_arm in per_model.items():
            if "base" in per_arm and "raar" in per_arm:
                task_level[task][model] = {
                    "base_mean": mean(per_arm["base"]),
                    "raar_mean": mean(per_arm["raar"]),
                }

    buckets = defaultdict(lambda: defaultdict(list))
    for task, per_model in task_level.items():
        task_meta = meta.get(task)
        if not task_meta:
            continue
        bucket = (task_meta["category"], task_meta["verifiability"])
        for model, row in per_model.items():
            buckets[bucket][model].append(row["raar_mean"] - row["base_mean"])

    ordered_bucket_keys = sorted(buckets)
    model_list = ordered_models(models)
    rows = []
    for category, verifiability in ordered_bucket_keys:
        per_model = {}
        aggregate_values = []
        total_tasks = 0
        for model in model_list:
            values = buckets[(category, verifiability)].get(model, [])
            delta = mean(values)
            per_model[model] = {"delta": delta, "n": len(values)}
            if values:
                aggregate_values.append(delta)
                total_tasks += len(values)
        overall = mean(aggregate_values)
        verdict = verdict_for(overall)
        rows.append({
            "category": category,
            "verifiability": verifiability,
            "models": per_model,
            "overall_delta": overall,
            "verdict": verdict,
            "reason": reason_for(verdict, per_model, total_tasks) if verdict else None,
        })

    payload = {
        "inputs": argv[1:],
        "rows": rows,
    }

    out_json = os.path.join("results", "v2", "domain_map.json")
    ensure_parent(out_json)
    with open(out_json, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)

    out_md = os.path.join("docs", "DOMAIN_MAP.md")
    ensure_parent(out_md)
    measured_rows = [row for row in rows if any(cell["delta"] is not None for cell in row["models"].values())]
    with open(out_md, "w") as handle:
        handle.write("# DOMAIN_MAP\n\n")
        handle.write("Derived from numeric checker scores only. Buckets with no scored base/RAAR overlap are omitted.\n\n")
        headers = ["Category", "Verifiability"]
        headers.extend("Delta %s" % model for model in model_list)
        headers.extend(["Verdict", "Reason"])
        handle.write("| " + " | ".join(headers) + " |\n")
        handle.write("| " + " | ".join("---" for _ in headers) + " |\n")
        for row in measured_rows:
            cells = [row["category"], row["verifiability"]]
            for model in model_list:
                cell = row["models"][model]
                if cell["delta"] is None:
                    cells.append("-")
                else:
                    cells.append("%.3f (n=%d)" % (cell["delta"], cell["n"]))
            cells.append(row["verdict"] or "-")
            cells.append(row["reason"] or "-")
            handle.write("| " + " | ".join(cells) + " |\n")

    print("category\tverifiability\t" + "\t".join(model_list) + "\tverdict")
    for row in measured_rows:
        fields = [row["category"], row["verifiability"]]
        for model in model_list:
            value = row["models"][model]["delta"]
            fields.append("%.3f" % value if value is not None else "-")
        fields.append(row["verdict"] or "-")
        print("\t".join(fields))
    print("wrote %s" % out_json)
    print("wrote %s" % out_md)


if __name__ == "__main__":
    main(sys.argv)
