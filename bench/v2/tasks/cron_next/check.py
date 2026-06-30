import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
HIDDEN_TESTS_PATH = ROOT / "reference" / "hidden_tests.json"
HIDDEN_TESTS = json.loads(HIDDEN_TESTS_PATH.read_text(encoding="utf-8"))
PYTHON_BLOCK_RE = re.compile(r"```python\s*(.*?)```", re.IGNORECASE | re.DOTALL)
SCRUBBED_ENV_KEYS = ("SYSTEMROOT", "WINDIR")
RUNNER = r"""
import importlib.util
import io
import json
import sys
from pathlib import Path


def load_module(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_next_fire(func, cron_expr, after_iso):
    return func(cron_expr, after_iso)


def main():
    payload = sys.stdin.read()
    sys.stdin = io.StringIO("")
    candidate_path = Path(sys.argv[1]).resolve()
    sys.argv = [sys.argv[0]]
    tests = json.loads(payload)

    try:
        module = load_module(candidate_path)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": 0,
                    "total": len(tests),
                    "failures": [{"index": -1, "error": f"import failed: {exc!r}"}],
                }
            )
        )
        return 0

    func = getattr(module, "next_fire", None)
    if not callable(func):
        print(json.dumps({"passed": 0, "total": len(tests), "failures": [{"index": -1, "error": "next_fire is missing or not callable"}]}))
        return 0

    passed = 0
    failures = []
    for index, test in enumerate(tests):
        try:
            actual = call_next_fire(func, test["cron_expr"], test["after_iso"])
        except Exception as exc:
            failures.append(
                {
                    "index": index,
                    "cron_expr": test["cron_expr"],
                    "after_iso": test["after_iso"],
                    "error": repr(exc),
                }
            )
            continue
        if actual == test["expected"]:
            passed += 1
        else:
            failures.append(
                {
                    "index": index,
                    "cron_expr": test["cron_expr"],
                    "after_iso": test["after_iso"],
                    "expected": test["expected"],
                    "actual": actual,
                }
            )
    print(json.dumps({"passed": passed, "total": len(tests), "failures": failures[:5]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def extract_last_python_block(answer_text):
    matches = PYTHON_BLOCK_RE.findall(answer_text)
    if not matches:
        raise ValueError("answer must contain at least one ```python ... ``` block")
    return matches[-1].strip() + "\n"


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


def score_answer(answer_path):
    answer_text = answer_path.read_text(encoding="utf-8")
    try:
        code = extract_last_python_block(answer_text)
    except ValueError as exc:
        return {"score": 0.0, "detail": {"error": str(exc)}}

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
                timeout=8,
                check=False,
                cwd=temp_path,
                env=build_scrubbed_env(str(temp_path)),
            )
        except subprocess.TimeoutExpired:
            return {"score": 0.0, "detail": {"error": "candidate execution timed out"}}

    if completed.returncode != 0:
        return {
            "score": 0.0,
            "detail": {
                "error": "candidate process failed",
                "stderr": completed.stderr.strip(),
                "stdout": completed.stdout.strip(),
            },
        }

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return {
            "score": 0.0,
            "detail": {
                "error": "runner did not emit valid JSON",
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            },
        }

    total = payload.get("total", 0)
    passed = payload.get("passed", 0)
    score = 0.0 if total == 0 else passed / total
    return {"score": score, "detail": payload}


def main(argv):
    if len(argv) != 2:
        print(json.dumps({"score": 0.0, "detail": {"error": "usage: python3 check.py <answer_file>"}}))
        return 1
    result = score_answer(Path(argv[1]))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
