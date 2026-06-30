import argparse
import json
import pathlib
import subprocess
import sys
from typing import Optional, TypedDict, Union


ROOT = pathlib.Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"
REQUIRED_KEYS = {
    "id": str,
    "category": str,
    "verifiability": str,
    "scoring": str,
    "prompt": str,
    "difficulty_rationale": list,
    "license": str,
}
CANDIDATE_REFERENCE_FILES = [
    "reference/answer.txt",
    "reference/answer.md",
    "reference/answer.csv",
    "reference/answer.jsonl",
    "reference/correct_answer.txt",
    "reference/solution.py",
    "reference/tokenizer.py",
]
HIDDEN_CASE_FILES = [
    "reference/hidden_tests.json",
    "reference/hidden_cases.json",
]
EXACT_ZERO_NEAR_MISS_POLICY = "exact_zero_allowed"


class ObjectiveResult(TypedDict):
    ref_score: Optional[float]
    near_miss_scores: list[tuple[str, float]]
    hidden_tests: Union[int, str]


def run_checker(check_path, answer_path):
    proc = subprocess.run(
        [sys.executable, str(check_path), str(answer_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "checker failed")
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("checker emitted invalid JSON") from exc
    if "score" not in payload:
        raise RuntimeError("checker JSON missing score")
    return payload


def extract_answer_value(payload):
    if isinstance(payload, dict):
        if "exact_answer" in payload:
            return payload["exact_answer"]
        if "answer" in payload:
            return payload["answer"]
    return payload


def infer_reference_answer(task_dir, payload):
    explicit = payload.get("reference_answer")
    if isinstance(explicit, str) and explicit:
        path = task_dir / explicit
        if path.exists():
            return path
    for candidate in CANDIDATE_REFERENCE_FILES:
        path = task_dir / candidate
        if path.exists():
            return path
    return None


def infer_hidden_test_count(task_dir):
    hidden_cases = load_hidden_cases(task_dir)
    return None if hidden_cases is None else len(hidden_cases)


def load_hidden_cases(task_dir):
    for relative in HIDDEN_CASE_FILES:
        path = task_dir / relative
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("tests", "cases"):
                if key in payload and isinstance(payload[key], list):
                    return payload[key]
        return None
    return None


def hidden_case_refs(cases):
    indexes = set(range(len(cases)))
    names = set()
    for case in cases:
        if isinstance(case, dict) and isinstance(case.get("name"), str):
            names.add(case["name"])
    return indexes, names


def discover_math_programs(task_dir):
    reference_dir = task_dir / "reference"
    ground_truth_path = reference_dir / "ground_truth.json"
    if not ground_truth_path.exists():
        return [], None
    ground_truth = json.loads(ground_truth_path.read_text(encoding="utf-8"))
    programs = []
    if isinstance(ground_truth.get("exact_methods"), dict):
        programs.extend(reference_dir / name for name in ground_truth["exact_methods"].keys())
    if isinstance(ground_truth.get("computed_by"), dict):
        for key, value in ground_truth["computed_by"].items():
            if isinstance(key, str) and key.endswith(".py"):
                programs.append(reference_dir / key)
            if isinstance(value, str) and value.endswith(".py"):
                programs.append(reference_dir / value)
    if isinstance(ground_truth.get("reference_programs"), list):
        programs.extend(reference_dir / name for name in ground_truth["reference_programs"] if isinstance(name, str))
    unique = []
    seen = set()
    for program in programs:
        if program.exists() and program not in seen:
            seen.add(program)
            unique.append(program)
    expected = extract_answer_value(ground_truth)
    return unique, expected


def requires_partial_near_miss(payload):
    if payload.get("category") == "math" and payload.get("near_miss_policy") == EXACT_ZERO_NEAR_MISS_POLICY:
        return False
    return True


def validate_near_miss_policy(payload, errors):
    policy = payload.get("near_miss_policy")
    if policy is None:
        return
    if policy != EXACT_ZERO_NEAR_MISS_POLICY:
        errors.append("unknown near_miss_policy %r" % policy)
        return
    if payload.get("category") != "math":
        errors.append("near_miss_policy %r is only valid for exact-answer math tasks" % policy)


def run_math_program(path):
    proc = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(path.parent),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "ground-truth program failed")
    text = proc.stdout.strip()
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return text.splitlines()[-1].strip()
    return extract_answer_value(payload)


def validate_math_ground_truth(task_dir, errors):
    programs, expected = discover_math_programs(task_dir)
    if not programs:
        errors.append("math task is missing discoverable ground-truth programs")
        return
    results = []
    for program in programs:
        try:
            results.append(run_math_program(program))
        except Exception as exc:  # noqa: BLE001
            errors.append("ground-truth program %s failed: %s" % (program.name, exc))
            return
    if len(results) < 2:
        errors.append("math task must provide at least two independent ground-truth programs")
        return
    if any(result != results[0] for result in results[1:]):
        errors.append("ground-truth programs disagree: %r" % results)
    if expected is not None and results[0] != expected:
        errors.append("ground-truth program result %r disagrees with ground_truth.json value %r" % (results[0], expected))


def validate_schema(task_dir, payload, errors):
    for key, kind in REQUIRED_KEYS.items():
        if key not in payload:
            errors.append("missing task.json key %r" % key)
            continue
        if not isinstance(payload[key], kind):
            errors.append("task.json key %r has wrong type" % key)
    if payload.get("verifiability") not in {"high", "medium", "low"}:
        errors.append("verifiability must be high, medium, or low")
    rationale = payload.get("difficulty_rationale", [])
    if not isinstance(rationale, list) or len(rationale) < 6:
        errors.append("difficulty_rationale must contain at least 6 entries")
    elif any(not isinstance(item, str) or not item.strip() for item in rationale):
        errors.append("difficulty_rationale entries must be non-empty strings")
    elif len(set(rationale)) != len(rationale):
        errors.append("difficulty_rationale entries must be distinct")
    if payload.get("license") != "MIT":
        errors.append("license must be MIT")
    if payload.get("id") != task_dir.name:
        errors.append("task.json id must match directory name")
    validate_near_miss_policy(payload, errors)


def validate_low_task(task_dir, payload, errors):
    rubric = payload.get("rubric_dims")
    if not isinstance(rubric, list) or not rubric or any(not isinstance(item, str) or not item.strip() for item in rubric):
        errors.append("low-verifiability tasks must define non-empty rubric_dims")
    if (task_dir / "check.py").exists():
        errors.append("judged tasks must not include check.py")


def validate_hidden_coverage(task_dir, payload, hidden_cases, errors):
    coverage = payload.get("hidden_coverage")
    if not isinstance(coverage, list) or not coverage:
        errors.append("hidden-test tasks must define non-empty hidden_coverage")
        return
    rationale = payload.get("difficulty_rationale", [])
    min_groups = min(6, len(rationale)) if isinstance(rationale, list) else 6
    if len(coverage) < min_groups:
        errors.append("hidden_coverage must contain at least %s rule groups" % min_groups)
    indexes, names = hidden_case_refs(hidden_cases)
    covered = set()
    for position, item in enumerate(coverage):
        if not isinstance(item, dict):
            errors.append("hidden_coverage[%s] must be an object" % position)
            continue
        rule = item.get("rule")
        cases = item.get("cases")
        if not isinstance(rule, str) or not rule.strip():
            errors.append("hidden_coverage[%s].rule must be a non-empty string" % position)
        if not isinstance(cases, list) or not cases:
            errors.append("hidden_coverage[%s].cases must be a non-empty list" % position)
            continue
        for case_ref in cases:
            if isinstance(case_ref, int):
                if case_ref not in indexes:
                    errors.append("hidden_coverage[%s] references missing case index %s" % (position, case_ref))
                else:
                    covered.add(case_ref)
            elif isinstance(case_ref, str):
                if case_ref not in names:
                    errors.append("hidden_coverage[%s] references missing case name %r" % (position, case_ref))
                else:
                    covered.add(case_ref)
            else:
                errors.append("hidden_coverage[%s] case refs must be indexes or names" % position)
    if len(covered) < min(20, len(hidden_cases)):
        errors.append("hidden_coverage must reference at least %s distinct hidden cases" % min(20, len(hidden_cases)))


def validate_objective_task(task_dir, payload, errors):
    check_path = task_dir / "check.py"
    reference_dir = task_dir / "reference"
    near_miss_dir = task_dir / "near_miss"
    expected_path = near_miss_dir / "expected.json"
    if not check_path.exists():
        errors.append("missing check.py")
        return None
    if not reference_dir.is_dir():
        errors.append("missing reference/ directory")
        return None
    if not near_miss_dir.is_dir():
        errors.append("missing near_miss/ directory")
        return None
    if not expected_path.exists():
        errors.append("missing near_miss/expected.json")
        return None
    ref_path = infer_reference_answer(task_dir, payload)
    if ref_path is None:
        errors.append("could not infer a reference answer file")
        return None
    result: ObjectiveResult = {"ref_score": None, "near_miss_scores": [], "hidden_tests": "-"}
    try:
        ref_payload = run_checker(check_path, ref_path)
        result["ref_score"] = float(ref_payload["score"])
        if result["ref_score"] != 1.0:
            errors.append("reference answer must score exactly 1.0")
    except Exception as exc:  # noqa: BLE001
        errors.append("reference check failed: %s" % exc)
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append("cannot parse near_miss/expected.json: %s" % exc)
        expected = {}
    if not isinstance(expected, dict) or not expected:
        errors.append("near_miss/expected.json must map at least one filename to a score range")
        expected = {}
    partial_found = False
    for name, bounds in expected.items():
        miss_path = near_miss_dir / name
        if not miss_path.exists():
            errors.append("near-miss file %r is missing" % name)
            continue
        if not (isinstance(bounds, list) and len(bounds) == 2 and all(isinstance(x, (int, float)) for x in bounds)):
            errors.append("near-miss range for %r must be [lo, hi]" % name)
            continue
        try:
            miss_payload = run_checker(check_path, miss_path)
            score = float(miss_payload["score"])
        except Exception as exc:  # noqa: BLE001
            errors.append("near-miss check failed for %r: %s" % (name, exc))
            continue
        lo, hi = bounds
        result["near_miss_scores"].append((name, score))
        if not (lo <= score <= hi):
            errors.append("near-miss %r scored %s outside declared range %s" % (name, score, bounds))
        if 0.0 < score < 1.0:
            partial_found = True
    if requires_partial_near_miss(payload) and not partial_found:
        errors.append("at least one near-miss must score strictly between 0 and 1")
    hidden_cases = load_hidden_cases(task_dir)
    hidden_count = None if hidden_cases is None else len(hidden_cases)
    if payload.get("category") == "math":
        validate_math_ground_truth(task_dir, errors)
    if payload.get("category") == "code" or payload.get("scoring") == "hidden_tests" or hidden_count is not None:
        if hidden_count is None:
            errors.append("code task is missing a discoverable hidden test case file")
        elif hidden_count < 20:
            errors.append("code-task hidden tests must cover at least 20 cases")
        else:
            validate_hidden_coverage(task_dir, payload, hidden_cases, errors)
        result["hidden_tests"] = hidden_count if hidden_count is not None else "-"
    return result


def format_table(rows):
    headers = ["task", "ref score", "near-miss scores", "#hidden tests", "status"]
    widths = [len(header) for header in headers]
    rendered = []
    for row in rows:
        values = [
            row["task"],
            row["ref_score"],
            row["near_miss"],
            row["hidden_tests"],
            row["status"],
        ]
        rendered.append(values)
        for idx, value in enumerate(values):
            widths[idx] = max(widths[idx], len(str(value)))
    lines = []
    header_line = " | ".join(str(header).ljust(widths[idx]) for idx, header in enumerate(headers))
    sep_line = "-+-".join("-" * width for width in widths)
    lines.extend([header_line, sep_line])
    for values in rendered:
        lines.append(" | ".join(str(value).ljust(widths[idx]) for idx, value in enumerate(values)))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="accepted for CLI compatibility; full validation still runs")
    args = parser.parse_args()
    _ = args.fast

    task_dirs = sorted(path for path in TASKS_DIR.iterdir() if path.is_dir())
    print("Validating task directories under bench/v2/tasks.")
    if not task_dirs:
        print("No task directories found.")
        return 0

    table_rows = []
    failures = []
    for task_dir in task_dirs:
        task_json = task_dir / "task.json"
        errors = []
        if not task_json.exists():
            errors.append("missing task.json")
            payload = {}
        else:
            try:
                payload = json.loads(task_json.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                payload = {}
                errors.append("cannot parse task.json: %s" % exc)
        if payload:
            validate_schema(task_dir, payload, errors)
            if payload.get("verifiability") == "low":
                validate_low_task(task_dir, payload, errors)
                ref_score = "n/a"
                near_miss = "n/a"
                hidden_tests = "-"
                status = "OK" if not errors else "FAIL"
            else:
                result = validate_objective_task(task_dir, payload, errors)
                ref_score = "n/a" if result is None or result["ref_score"] is None else str(result["ref_score"])
                near_miss = (
                    "n/a"
                    if result is None
                    else ", ".join("%s=%s" % (name, score) for name, score in result["near_miss_scores"])
                )
                hidden_tests = "-" if result is None else str(result["hidden_tests"])
                status = "OK" if not errors else "FAIL"
        else:
            ref_score = "n/a"
            near_miss = "n/a"
            hidden_tests = "-"
            status = "FAIL"
        table_rows.append(
            {
                "task": task_dir.name,
                "ref_score": ref_score,
                "near_miss": near_miss,
                "hidden_tests": hidden_tests,
                "status": status,
            }
        )
        if errors:
            failures.append((task_dir.name, errors))

    print(format_table(table_rows))
    if failures:
        print("\nValidation errors:")
        for task_name, errors in failures:
            print("- %s" % task_name)
            for error in errors:
                print("  * %s" % error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
