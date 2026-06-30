import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


THIS_DIR = Path(__file__).resolve().parent
HIDDEN_CASES = json.loads((THIS_DIR / "reference" / "hidden_cases.json").read_text(encoding="utf-8"))
HIDDEN_EXPECTED = json.loads((THIS_DIR / "reference" / "hidden_expected.json").read_text(encoding="utf-8"))
TIMEOUT_SECONDS = 5
SCRUBBED_ENV_KEYS = ("SYSTEMROOT", "WINDIR")
RUNNER = r"""
import importlib.util
import io
import json
import sys
from pathlib import Path


def load_module(path):
    spec = importlib.util.spec_from_file_location("submission", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def call_render_table(func, rows, widths, aligns):
    return func(rows, widths, aligns)


def main():
    payload = json.loads(sys.stdin.read())
    sys.stdin = io.StringIO("")
    submission_path = Path(sys.argv[1]).resolve()
    sys.argv = [sys.argv[0]]
    cases = payload["cases"]
    expected = payload["expected"]

    try:
        module = load_module(submission_path)
    except Exception as exc:
        print(json.dumps({"passed": 0, "total": len(cases), "failures": [{"name": case["name"], "error": "import_error", "message": repr(exc)} for case in cases]}))
        return

    fn = getattr(module, "render_table", None)
    if not callable(fn):
        print(json.dumps({"passed": 0, "total": len(cases), "failures": [{"name": case["name"], "error": "missing_render_table"} for case in cases]}))
        return

    passed = 0
    failures = []
    for case in cases:
        try:
            actual = call_render_table(fn, case["rows"], case["widths"], case["aligns"])
        except Exception as exc:
            failures.append({"name": case["name"], "error": "runtime_error", "message": repr(exc)})
            continue
        wanted = expected[case["name"]]
        if actual == wanted:
            passed += 1
        else:
            failures.append({"name": case["name"], "error": "wrong_answer", "expected": wanted, "actual": actual})
    print(json.dumps({"passed": passed, "total": len(cases), "failures": failures}))


if __name__ == "__main__":
    main()
"""


def _extract_last_python_block(text):
    matches = re.findall(r"```python\s*\n(.*?)```", text, flags=re.S)
    if not matches:
        return None
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


def _run_submission(answer_path):
    answer_text = Path(answer_path).read_text(encoding="utf-8")
    code = _extract_last_python_block(answer_text)
    if code is None:
        return {
            "score": 0.0,
            "detail": {
                "error": "no_python_code_block",
                "passed": 0,
                "total": 0
            }
        }

    payload = {"cases": HIDDEN_CASES, "expected": HIDDEN_EXPECTED}
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        submission_path = tmpdir_path / "submission.py"
        submission_path.write_text(code, encoding="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, "-I", "-B", "-c", RUNNER, str(submission_path)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
                cwd=tmpdir_path,
                env=build_scrubbed_env(str(tmpdir_path)),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return {
                "score": 0.0,
                "detail": {
                    "error": "timeout",
                    "passed": 0,
                    "total": 0
                }
            }
    if proc.returncode != 0:
        return {
            "score": 0.0,
            "detail": {
                "error": "checker_subprocess_failed",
                "returncode": proc.returncode,
                "stderr": proc.stderr.strip()
            }
        }
    detail = json.loads(proc.stdout)
    total = detail["total"]
    score = 0.0 if total == 0 else detail["passed"] / total
    return {"score": score, "detail": detail}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 check.py <answer_file>")
    print(json.dumps(_run_submission(sys.argv[1])))


if __name__ == "__main__":
    main()
