"""Checker for interval_sched."""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
HIDDEN_TESTS = json.loads((HERE / "reference" / "hidden_tests.json").read_text(encoding="utf-8"))
TIMEOUT_SECONDS = 10
SCRUBBED_ENV_KEYS = ("SYSTEMROOT", "WINDIR")

RUNNER = r"""
import importlib.util
import io
import json
import sys
import traceback
from pathlib import Path


def load_module(path):
    spec = importlib.util.spec_from_file_location("candidate_module", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_weighted_interval_schedule(func, intervals):
    return func(intervals)


def main():
    payload = json.loads(sys.stdin.read())
    sys.stdin = io.StringIO("")
    candidate_path = Path(sys.argv[1]).resolve()
    sys.argv = [sys.argv[0]]
    tests = payload["tests"]

    try:
        module = load_module(candidate_path)
    except Exception:
        print(json.dumps({
            "passed": 0,
            "total": 1,
            "failures": ["import failed\n" + traceback.format_exc()],
        }))
        return

    func = getattr(module, "weighted_interval_schedule", None)
    if not callable(func):
        print(json.dumps({
            "passed": 0,
            "total": 1,
            "failures": ["missing callable weighted_interval_schedule"],
        }))
        return

    failures = []
    passed = 0
    for case in tests:
        intervals = [tuple(item) for item in case["intervals"]]
        before = list(intervals)
        try:
            result = call_weighted_interval_schedule(func, intervals)
        except Exception:
            failures.append(case["name"] + ": raised\n" + traceback.format_exc())
            continue

        if intervals != before:
            failures.append(case["name"] + ": input list was mutated")
            continue

        if not isinstance(result, tuple) or len(result) != 2 or not isinstance(result[1], list):
            failures.append(case["name"] + ": expected a tuple (best_weight, chosen_ids_list)")
            continue

        best_weight, chosen_ids = result
        if best_weight != case["expected_weight"] or chosen_ids != case["expected_ids"]:
            failures.append(
                "%s: expected (%r, %r), got (%r, %r)" % (
                    case["name"],
                    case["expected_weight"],
                    case["expected_ids"],
                    best_weight,
                    chosen_ids,
                )
            )
            continue
        passed += 1

    print(json.dumps({
        "passed": passed,
        "total": len(tests),
        "failures": failures[:10],
    }))


if __name__ == "__main__":
    main()
"""


def extract_last_python_block(text):
    blocks = re.findall(r"```python\s*\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return blocks[-1] if blocks else None


def build_scrubbed_env(temp_dir):
    env = {
        "PYTHONIOENCODING": "utf-8",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUTF8": "1",
        "TMPDIR": temp_dir,
        "TMP": temp_dir,
        "TEMP": temp_dir,
    }
    for key in SCRUBBED_ENV_KEYS:
        value = os.environ.get(key)
        if value:
            env[key] = value
    return env


def score_answer(answer_file):
    with open(answer_file, "r", encoding="utf-8") as handle:
        answer_text = handle.read()
    code = extract_last_python_block(answer_text)
    if code is None:
        return {
            "score": 0.0,
            "detail": {
                "passed": 0,
                "total": 1,
                "failures": ["no ```python block found"],
            },
        }

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        candidate_path = temp_path / "candidate.py"
        candidate_path.write_text(code, encoding="utf-8")

        try:
            completed = subprocess.run(
                [sys.executable, "-I", "-B", "-c", RUNNER, str(candidate_path)],
                input=json.dumps(HIDDEN_TESTS),
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                check=False,
                cwd=temp_path,
                env=build_scrubbed_env(str(temp_path)),
            )
        except subprocess.TimeoutExpired:
            return {
                "score": 0.0,
                "detail": {
                    "passed": 0,
                    "total": 1,
                    "failures": ["timeout after %s seconds" % TIMEOUT_SECONDS],
                },
            }

    try:
        detail = json.loads(completed.stdout.strip())
    except json.JSONDecodeError:
        detail = {
            "passed": 0,
            "total": 1,
            "failures": [
                "runner emitted invalid JSON",
                "stdout: %r" % completed.stdout,
                "stderr: %r" % completed.stderr,
            ],
        }
    passed = detail.get("passed", 0)
    total = detail.get("total", 1)
    if not isinstance(passed, (int, float)):
        passed = 0
    if not isinstance(total, (int, float)):
        total = 1
    score = float(passed) / max(float(total), 1.0)
    return {"score": score, "detail": detail}


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: python3 check.py <answer_file>")
    result = score_answer(argv[1])
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
