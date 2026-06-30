"""Summarize scored v2 runs.

Usage:
    python3 analysis/v2_stats.py <scored.json...>

Input files are JSON lists of run dicts, typically containing:
    {task, arm, model, seed, answer, calls, score?, score_detail?, verdicts?}

Outputs:
    - results/v2/stats.json
    - human-readable tables on stdout
"""
import json
import os
import random
import sys
from collections import defaultdict


MODEL_ORDER = ["haiku", "sonnet", "opus", "fable"]


def usage():
    raise SystemExit("usage: python3 analysis/v2_stats.py <scored.json...>")


def mean(values):
    return sum(values) / len(values) if values else None


def percentile(sorted_values, pct):
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * (pct / 100.0)
    low = int(pos)
    high = min(low + 1, len(sorted_values) - 1)
    frac = pos - low
    return sorted_values[low] * (1.0 - frac) + sorted_values[high] * frac


def bootstrap_ci(values, seed, resamples=10000):
    if not values:
        return None
    if len(values) == 1:
        return [values[0], values[0]]
    rng = random.Random(seed)
    n_values = len(values)
    samples = []
    for _ in range(resamples):
        draw = [values[rng.randrange(n_values)] for _ in range(n_values)]
        samples.append(sum(draw) / n_values)
    samples.sort()
    return [percentile(samples, 2.5), percentile(samples, 97.5)]


def permutation_test(differences, seed, perms=10000):
    if not differences:
        return None
    observed = sum(differences) / len(differences)
    rng = random.Random(seed)
    extreme = 0
    for _ in range(perms):
        signed = 0.0
        for diff in differences:
            signed += diff if rng.randrange(2) else -diff
        stat = signed / len(differences)
        if abs(stat) >= abs(observed) - 1e-12:
            extreme += 1
    return {
        "n_tasks": len(differences),
        "observed_diff": observed,
        "p_value": (extreme + 1) / float(perms + 1),
        "permutations": perms,
    }


def key_of(run):
    task = run.get("task", run.get("taskId"))
    arm = run.get("arm")
    model = run.get("model")
    return task, arm, model


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
            task, arm, model = key_of(run)
            if task is None or arm is None or model is None:
                continue
            run = dict(run)
            run["task"] = task
            runs.append(run)
    return runs


def numeric_score(run):
    value = run.get("score")
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def ordered_models(models):
    known = [model for model in MODEL_ORDER if model in models]
    extra = sorted(model for model in models if model not in MODEL_ORDER)
    return known + extra


def ordered_keys(keys):
    def sort_key(cell_key):
        arm, model = cell_key.split("@", 1)
        model_rank = MODEL_ORDER.index(model) if model in MODEL_ORDER else len(MODEL_ORDER)
        return (model_rank, model, arm)

    return sorted(keys, key=sort_key)


def build_tables(runs):
    score_table = defaultdict(lambda: defaultdict(list))
    task_arm_model_runs = defaultdict(list)
    models = set()
    arms = set()
    for run in runs:
        task, arm, model = run["task"], run["arm"], run["model"]
        models.add(model)
        arms.add(arm)
        key = "%s@%s" % (arm, model)
        task_arm_model_runs[(task, key)].append(run)
        score = numeric_score(run)
        if score is not None:
            score_table[task][key].append(score)

    cell_stats = {}
    for task in sorted(score_table):
        cell_stats[task] = {}
        for key in ordered_keys(score_table[task]):
            values = score_table[task][key]
            cell_stats[task][key] = {
                "mean": mean(values),
                "n": len(values),
                "scores": list(values),
            }
    return cell_stats, task_arm_model_runs, ordered_models(models), sorted(arms)


def macro_stats(cell_stats):
    all_keys = set()
    for task in cell_stats.values():
        all_keys.update(task.keys())
    summary = {}
    for index, key in enumerate(ordered_keys(all_keys)):
        task_means = {}
        for task in sorted(cell_stats):
            cell = cell_stats[task].get(key)
            if cell:
                task_means[task] = cell["mean"]
        values = [task_means[task] for task in sorted(task_means)]
        summary[key] = {
            "mean": mean(values),
            "n_tasks": len(values),
            "ci95": bootstrap_ci(values, 42 + index) if values else None,
            "task_means": task_means,
        }
    return summary


def paired_task_diffs(cell_stats, key_a, key_b):
    overlaps = []
    for task in sorted(cell_stats):
        cell_a = cell_stats[task].get(key_a)
        cell_b = cell_stats[task].get(key_b)
        if cell_a and cell_b:
            overlaps.append((task, cell_a["mean"] - cell_b["mean"]))
    return overlaps


def permutation_tests(cell_stats, models, arms):
    results = []
    seed = 4200
    for model in models:
        key_a = "raar@%s" % model
        key_b = "base@%s" % model
        overlaps = paired_task_diffs(cell_stats, key_a, key_b)
        payload = {
            "contrast": "%s vs %s" % (key_a, key_b),
            "a": key_a,
            "b": key_b,
            "tasks": [task for task, _ in overlaps],
        }
        if overlaps:
            payload.update(permutation_test([diff for _, diff in overlaps], seed))
        else:
            payload.update({"n_tasks": 0, "observed_diff": None, "p_value": None, "permutations": 10000})
        results.append(payload)
        seed += 1

    key_a = "raar@sonnet"
    key_b = "base@fable"
    overlaps = paired_task_diffs(cell_stats, key_a, key_b)
    payload = {
        "contrast": "%s vs %s" % (key_a, key_b),
        "a": key_a,
        "b": key_b,
        "tasks": [task for task, _ in overlaps],
    }
    if overlaps:
        payload.update(permutation_test([diff for _, diff in overlaps], seed))
    else:
        payload.update({"n_tasks": 0, "observed_diff": None, "p_value": None, "permutations": 10000})
    results.append(payload)
    seed += 1

    ablations = sorted(arm for arm in arms if arm not in ("base", "raar"))
    for arm in ablations:
        key_a = "%s@sonnet" % arm
        key_b = "raar@sonnet"
        overlaps = paired_task_diffs(cell_stats, key_a, key_b)
        payload = {
            "contrast": "%s vs %s" % (key_a, key_b),
            "a": key_a,
            "b": key_b,
            "tasks": [task for task, _ in overlaps],
        }
        if overlaps:
            payload.update(permutation_test([diff for _, diff in overlaps], seed))
        else:
            payload.update({"n_tasks": 0, "observed_diff": None, "p_value": None, "permutations": 10000})
        results.append(payload)
        seed += 1
    return results


def degradation_counts(runs, cell_stats):
    base_means = {}
    for task, task_cells in cell_stats.items():
        for key, cell in task_cells.items():
            arm, model = key.split("@", 1)
            if arm == "base":
                base_means[(task, model)] = cell["mean"]

    summary = defaultdict(lambda: {"count": 0, "total_compared": 0})
    for run in runs:
        score = numeric_score(run)
        if score is None:
            continue
        task, arm, model = run["task"], run["arm"], run["model"]
        baseline = base_means.get((task, model))
        if baseline is None:
            continue
        key = "%s@%s" % (arm, model)
        summary[key]["total_compared"] += 1
        if score < baseline:
            summary[key]["count"] += 1

    result = {}
    for key in ordered_keys(summary):
        row = dict(summary[key])
        total = row["total_compared"]
        row["rate"] = (row["count"] / float(total)) if total else None
        result[key] = row
    return result


def gap_closure(cell_stats, models):
    per_model = {}
    for index, model in enumerate(models):
        task_rows = {}
        values = []
        for task in sorted(cell_stats):
            base_model = cell_stats[task].get("base@%s" % model)
            raar_model = cell_stats[task].get("raar@%s" % model)
            base_fable = cell_stats[task].get("base@fable")
            if not base_model or not raar_model or not base_fable:
                continue
            denominator = base_fable["mean"] - base_model["mean"]
            if denominator <= 0.05:
                continue
            numerator = raar_model["mean"] - base_model["mean"]
            value = numerator / denominator
            task_rows[task] = {
                "value": value,
                "numerator": numerator,
                "denominator": denominator,
            }
            values.append(value)
        per_model[model] = {
            "per_task": task_rows,
            "overall": {
                "mean": mean(values),
                "n_tasks": len(values),
                "ci95": bootstrap_ci(values, 5200 + index) if values else None,
            },
        }
    return per_model


def ensure_parent(path):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def print_task_table(cell_stats):
    all_keys = set()
    for task in cell_stats.values():
        all_keys.update(task.keys())
    cols = ordered_keys(all_keys)
    width = 24
    print("Per-task means")
    print("%-24s%s" % ("task", "".join("%*s" % (width, key) for key in cols)))
    for task in sorted(cell_stats):
        row = "%-24s" % task
        for key in cols:
            cell = cell_stats[task].get(key)
            if cell:
                label = "%.3f (n=%d)" % (cell["mean"], cell["n"])
            else:
                label = "-"
            row += "%*s" % (width, label)
        print(row)
    print()


def print_macro_table(macros):
    print("Macro means")
    print("%-22s %8s %8s %24s" % ("arm@model", "macro", "n", "95% CI"))
    for key in ordered_keys(macros):
        row = macros[key]
        ci = row["ci95"]
        ci_text = "[%.3f, %.3f]" % (ci[0], ci[1]) if ci else "-"
        macro = "%.3f" % row["mean"] if row["mean"] is not None else "-"
        print("%-22s %8s %8d %24s" % (key, macro, row["n_tasks"], ci_text))
    print()


def print_tests(tests):
    print("Paired permutation tests")
    print("%-34s %6s %10s %10s" % ("contrast", "n", "diff", "p"))
    for row in tests:
        diff = "%.3f" % row["observed_diff"] if row["observed_diff"] is not None else "-"
        p_value = "%.4f" % row["p_value"] if row["p_value"] is not None else "-"
        print("%-34s %6d %10s %10s" % (row["contrast"], row["n_tasks"], diff, p_value))
    print()


def print_degradation(degradation):
    print("Degradation counts")
    print("%-22s %10s %10s %10s" % ("arm@model", "count", "total", "rate"))
    for key in ordered_keys(degradation):
        row = degradation[key]
        rate = "%.3f" % row["rate"] if row["rate"] is not None else "-"
        print("%-22s %10d %10d %10s" % (key, row["count"], row["total_compared"], rate))
    print()


def print_gap_closure(gaps):
    print("Gap closure")
    print("%-12s %8s %8s %24s" % ("model", "mean", "n", "95% CI"))
    for model in ordered_models(gaps):
        row = gaps[model]["overall"]
        ci = row["ci95"]
        ci_text = "[%.3f, %.3f]" % (ci[0], ci[1]) if ci else "-"
        macro = "%.3f" % row["mean"] if row["mean"] is not None else "-"
        print("%-12s %8s %8d %24s" % (model, macro, row["n_tasks"], ci_text))
    print()


def main(argv):
    if len(argv) < 2:
        usage()
    runs = load_runs(argv[1:])
    cell_stats, _, models, arms = build_tables(runs)
    macros = macro_stats(cell_stats)
    tests = permutation_tests(cell_stats, models, arms)
    degradation = degradation_counts(runs, cell_stats)
    gaps = gap_closure(cell_stats, models)

    payload = {
        "inputs": argv[1:],
        "run_count": len(runs),
        "task_arm_model": cell_stats,
        "macro": macros,
        "permutation_tests": tests,
        "degradation": degradation,
        "gap_closure": gaps,
    }

    out_path = os.path.join("results", "v2", "stats.json")
    ensure_parent(out_path)
    with open(out_path, "w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)

    print("Merged %d runs from %d file(s)" % (len(runs), len(argv) - 1))
    print()
    print_task_table(cell_stats)
    print_macro_table(macros)
    print_tests(tests)
    print_degradation(degradation)
    print_gap_closure(gaps)
    print("wrote %s" % out_path)


if __name__ == "__main__":
    main(sys.argv)
