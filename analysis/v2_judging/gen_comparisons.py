"""Generate blinded pairwise comparison files for v2 judged tasks.

Usage:
    python3 analysis/v2_judging/gen_comparisons.py <runs.json>
"""
import json
import os
import sys


PAIR_SPECS = [
    ("raar@sonnet", "base@fable"),
    ("base@sonnet", "base@fable"),
    ("raar@sonnet", "base@sonnet"),
    ("raar@fable", "base@fable"),
    ("raar@haiku", "base@haiku"),
]
TASK_IDS = ["design_pipeline", "explain_raft", "migration_plan"]
OUT_DIR = os.path.join("results", "v2", "judging")

JUDGE_PROMPT = """You are an expert judge comparing two anonymous answers to the same task.
Judge ONLY on these rubric dimensions:
- {dims}

Ignore length and stylistic flourishes except where the task explicitly requires them.
Penalize technical inaccuracies heavily.

=== TASK ===
{task_prompt}

=== ANSWER A ===
{answer_a}

=== ANSWER B ===
{answer_b}

Briefly compare the answers dimension by dimension, then end your reply with exactly one line: "WINNER: A" or "WINNER: B" or "WINNER: TIE".
"""


def usage():
    raise SystemExit("usage: python3 analysis/v2_judging/gen_comparisons.py <runs.json>")


def load_task_configs():
    configs = {}
    root = os.path.join("bench", "v2", "tasks")
    for task_id in TASK_IDS:
        path = os.path.join(root, task_id, "task.json")
        with open(path) as handle:
            configs[task_id] = json.load(handle)
    return configs


def normalize_task(run):
    return run.get("task", run.get("taskId"))


def load_runs(path):
    with open(path) as handle:
        payload = json.load(handle)
    if isinstance(payload, dict) and isinstance(payload.get("runs"), list):
        payload = payload["runs"]
    if not isinstance(payload, list):
        raise ValueError("%s is not a JSON list or {runs:[...]}" % path)
    grouped = {}
    for run in payload:
        if not isinstance(run, dict):
            continue
        arm = run.get("arm")
        model = run.get("model")
        if arm is None or model is None:
            continue
        label = "%s@%s" % (arm, model)
        task = normalize_task(run)
        if task in TASK_IDS and run.get("answer") is not None:
            grouped.setdefault((task, label), []).append(run)
            continue
        for field in ("answers", "judged_answers", "responses", "outputs"):
            nested = run.get(field)
            if not isinstance(nested, dict):
                continue
            for task_id in TASK_IDS:
                answer = nested.get(task_id)
                if isinstance(answer, dict):
                    answer = answer.get("answer", answer.get("text"))
                if answer is None:
                    continue
                grouped.setdefault((task_id, label), []).append({
                    "task": task_id,
                    "arm": arm,
                    "model": model,
                    "seed": run.get("seed"),
                    "answer": answer,
                })

    for key in grouped:
        grouped[key].sort(key=lambda run: (run.get("seed") is None, run.get("seed"), run.get("answer", "")))
    return grouped


def cleanup_output_dir():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name in os.listdir(OUT_DIR):
        if name.startswith("cmp") and name.endswith(".txt"):
            os.unlink(os.path.join(OUT_DIR, name))


def format_dims(dims):
    return "\n- ".join(dims)


def paired_runs(left_runs, right_runs):
    return list(zip(left_runs, right_runs))


def main(argv):
    if len(argv) != 2:
        usage()

    cleanup_output_dir()
    configs = load_task_configs()
    grouped = load_runs(argv[1])

    manifest = []
    counter = 0
    for task_id in TASK_IDS:
        config = configs[task_id]
        dims = format_dims(config.get("rubric_dims", []))
        for left_label, right_label in PAIR_SPECS:
            left_runs = grouped.get((task_id, left_label), [])
            right_runs = grouped.get((task_id, right_label), [])
            if not left_runs or not right_runs:
                continue
            for pair_index, (left_run, right_run) in enumerate(paired_runs(left_runs, right_runs)):
                for order in (0, 1):
                    cmp_id = "cmp%02d" % counter
                    if order == 0:
                        answer_a = left_run["answer"]
                        answer_b = right_run["answer"]
                        answer_a_label = left_label
                        answer_b_label = right_label
                    else:
                        answer_a = right_run["answer"]
                        answer_b = left_run["answer"]
                        answer_a_label = right_label
                        answer_b_label = left_label
                    prompt = JUDGE_PROMPT.format(
                        dims=dims,
                        task_prompt=config.get("prompt", ""),
                        answer_a=answer_a,
                        answer_b=answer_b,
                    )
                    cmp_path = os.path.join(OUT_DIR, cmp_id + ".txt")
                    with open(cmp_path, "w") as handle:
                        handle.write(prompt)
                    manifest.append({
                        "id": cmp_id,
                        "task": task_id,
                        "pair": [left_label, right_label],
                        "pair_index": pair_index,
                        "order": order,
                        "A": answer_a_label,
                        "B": answer_b_label,
                        "left_seed": left_run.get("seed"),
                        "right_seed": right_run.get("seed"),
                        "file": cmp_path,
                    })
                    counter += 1

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w") as handle:
        json.dump(manifest, handle, indent=2)

    print("wrote %d comparisons to %s" % (len(manifest), OUT_DIR))
    print("wrote %s" % manifest_path)


if __name__ == "__main__":
    main(sys.argv)
