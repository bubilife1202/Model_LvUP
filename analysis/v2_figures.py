"""Render v2 analysis figures.

Usage:
    uv run --with matplotlib analysis/v2_figures.py <scored.json...>

Outputs:
    - paper/fig_ladder.pdf
    - paper/fig_domain.pdf
    - paper/fig_cost.pdf
"""
import json
import os
import random
import sys
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


MODEL_ORDER = ["haiku", "sonnet", "opus", "fable"]
ARM_STYLES = {
    "base": {"label": "base", "color": "#4C566A"},
    "raar": {"label": "+RAAR", "color": "#BF616A"},
}


def usage():
    raise SystemExit("usage: uv run --with matplotlib analysis/v2_figures.py <scored.json...>")


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
    samples = []
    count = len(values)
    for _ in range(resamples):
        draw = [values[rng.randrange(count)] for _ in range(count)]
        samples.append(sum(draw) / count)
    samples.sort()
    return [percentile(samples, 2.5), percentile(samples, 97.5)]


def ordered_models(models):
    known = [model for model in MODEL_ORDER if model in models]
    extra = sorted(model for model in models if model not in MODEL_ORDER)
    return known + extra


def numeric_score(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def call_count(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return float(len(value))
    return None


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
            if task is None or arm is None or model is None:
                continue
            runs.append({
                "task": task,
                "arm": arm,
                "model": model,
                "score": numeric_score(run.get("score")),
                "calls": call_count(run.get("calls")),
            })
    return runs


def load_task_meta():
    meta = {}
    root = os.path.join("bench", "v2", "tasks")
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


def build_score_tables(runs):
    scores = defaultdict(lambda: defaultdict(list))
    calls = defaultdict(list)
    models = set()
    for run in runs:
        key = "%s@%s" % (run["arm"], run["model"])
        models.add(run["model"])
        if run["score"] is not None:
            scores[run["task"]][key].append(run["score"])
        if run["calls"] is not None:
            calls[key].append(run["calls"])
    task_means = defaultdict(dict)
    for task, task_scores in scores.items():
        for key, values in task_scores.items():
            task_means[task][key] = mean(values)
    return task_means, calls, ordered_models(models)


def macro_for(task_means, key):
    values = [task_means[task][key] for task in sorted(task_means) if key in task_means[task]]
    return mean(values), values


def ensure_outdir(path):
    os.makedirs(path, exist_ok=True)


def main(argv):
    if len(argv) < 2:
        usage()
    runs = load_runs(argv[1:])
    meta = load_task_meta()
    task_means, calls, models = build_score_tables(runs)
    ensure_outdir("paper")

    # fig_ladder.pdf
    fig, ax = plt.subplots(figsize=(6.2, 3.6))
    xs = list(range(len(models)))
    base_fable = None
    for arm_index, arm in enumerate(("base", "raar")):
        y_values = []
        y_err_low = []
        y_err_high = []
        x_values = []
        for model_index, model in enumerate(models):
            key = "%s@%s" % (arm, model)
            macro, per_task = macro_for(task_means, key)
            if macro is None:
                continue
            ci = bootstrap_ci(per_task, 42 + arm_index * 100 + model_index)
            x_values.append(model_index)
            y_values.append(macro)
            if ci:
                y_err_low.append(macro - ci[0])
                y_err_high.append(ci[1] - macro)
            else:
                y_err_low.append(0.0)
                y_err_high.append(0.0)
            if key == "base@fable":
                base_fable = macro
        if x_values:
            ax.errorbar(
                x_values,
                y_values,
                yerr=[y_err_low, y_err_high],
                color=ARM_STYLES[arm]["color"],
                marker="o",
                lw=1.8,
                capsize=3,
                label=ARM_STYLES[arm]["label"],
            )
    if base_fable is not None:
        ax.axhline(base_fable, color="#2E3440", ls="--", lw=1.0, alpha=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels(models)
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("macro score")
    ax.set_title("Macro quality across the model ladder")
    ax.legend(frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join("paper", "fig_ladder.pdf"))
    plt.close(fig)

    # fig_domain.pdf
    sonnet_deltas = defaultdict(list)
    for task, task_rows in task_means.items():
        base_key = "base@sonnet"
        raar_key = "raar@sonnet"
        if base_key not in task_rows or raar_key not in task_rows:
            continue
        task_meta = meta.get(task)
        if not task_meta:
            continue
        sonnet_deltas[task_meta["category"]].append(task_rows[raar_key] - task_rows[base_key])
    categories = sorted(sonnet_deltas)
    fig, ax = plt.subplots(figsize=(7.0, 3.6))
    bar_values = [mean(sonnet_deltas[category]) for category in categories]
    colors = ["#A3BE8C" if value >= 0 else "#D08770" for value in bar_values]
    ax.bar(range(len(categories)), bar_values, color=colors, width=0.72)
    ax.axhline(0.0, color="#4C566A", lw=1.0)
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=25, ha="right")
    ax.set_ylabel("RAAR - base")
    ax.set_title("Sonnet deltas by category")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join("paper", "fig_domain.pdf"))
    plt.close(fig)

    # fig_cost.pdf
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    points = []
    for key in sorted(calls):
        macro, _ = macro_for(task_means, key)
        if macro is None:
            continue
        mean_calls = mean(calls[key])
        if mean_calls is None:
            continue
        arm = key.split("@", 1)[0]
        color = ARM_STYLES.get(arm, {"color": "#5E81AC"})["color"]
        points.append((mean_calls, macro, key, color))
    for x_value, y_value, label, color in points:
        ax.scatter([x_value], [y_value], s=42, color=color)
        ax.annotate(label, (x_value, y_value), textcoords="offset points", xytext=(4, 4), fontsize=8)
    ax.set_xlabel("mean calls")
    ax.set_ylabel("macro score")
    ax.set_title("Quality vs inference cost")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(os.path.join("paper", "fig_cost.pdf"))
    plt.close(fig)

    print("wrote paper/fig_ladder.pdf")
    print("wrote paper/fig_domain.pdf")
    print("wrote paper/fig_cost.pdf")


if __name__ == "__main__":
    main(sys.argv)
