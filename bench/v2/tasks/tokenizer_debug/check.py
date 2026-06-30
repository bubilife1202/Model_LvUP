import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parent
HIDDEN_CASES = json.loads((TASK_DIR / "reference" / "hidden_cases.json").read_text(encoding="utf-8"))
HIDDEN_EXPECTED = json.loads((TASK_DIR / "reference" / "hidden_expected.json").read_text(encoding="utf-8"))
PYTHON_BLOCK_RE = re.compile(r"```python\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)
SCRUBBED_ENV_KEYS = ("SYSTEMROOT", "WINDIR")
RUNNER = r"""
import importlib.util
import io
import json
import sys
from pathlib import Path


def serialize(tokens):
    return [
        {"kind": token.kind, "value": token.value, "line": token.line, "col": token.col}
        for token in tokens
    ]


def load_candidate(path):
    spec = importlib.util.spec_from_file_location("candidate_tokenizer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_case(module, case):
    try:
        return {"tokens": serialize(module.tokenize(case["src"]))}
    except Exception as exc:
        return {"error": {"type": type(exc).__name__, "message": str(exc)}}


def main():
    payload = json.loads(sys.stdin.read())
    sys.stdin = io.StringIO("")
    candidate_path = Path(sys.argv[1]).resolve()
    sys.argv = [sys.argv[0]]
    cases = payload["cases"]
    expected = payload["expected"]

    try:
        module = load_candidate(candidate_path)
        getattr(module, "tokenize")
        getattr(module, "Token")
    except Exception as exc:
        print(
            json.dumps(
                {
                    "passed": 0,
                    "total": len(cases),
                    "failures": [f"import error: {type(exc).__name__}: {exc}"],
                }
            )
        )
        return

    passed = 0
    failures = []
    for case in cases:
        actual = run_case(module, case)
        if actual == expected[case["name"]]:
            passed += 1
        else:
            failures.append(
                {
                    "name": case["name"],
                    "expected": expected[case["name"]],
                    "actual": actual,
                }
            )

    print(json.dumps({"passed": passed, "total": len(cases), "failures": failures}))


if __name__ == "__main__":
    main()
"""


def extract_last_python_block(text):
    blocks = PYTHON_BLOCK_RE.findall(text)
    if not blocks:
        raise ValueError("answer must contain at least one ```python block")
    return blocks[-1].strip() + "\n"


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


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "detail": {"error": "usage: python3 check.py <answer_file>"}}))
        return

    answer_path = Path(sys.argv[1])
    try:
        code = extract_last_python_block(answer_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "detail": {"error": str(exc)}}))
        return

    payload = {"cases": HIDDEN_CASES, "expected": HIDDEN_EXPECTED}
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        candidate_path = tmp_path / "candidate.py"
        candidate_path.write_text(code, encoding="utf-8")
        cmd = [sys.executable, "-I", "-B", "-c", RUNNER, str(candidate_path)]
        try:
            proc = subprocess.run(
                cmd,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                cwd=tmp_path,
                env=build_scrubbed_env(str(tmp_path)),
            )
        except subprocess.TimeoutExpired:
            print(json.dumps({"score": 0.0, "detail": {"error": "hidden tests timed out"}}))
            return

    try:
        detail = json.loads(proc.stdout.strip() or "{}")
        passed = int(detail["passed"])
        total = int(detail["total"])
    except Exception:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "detail": {
                        "error": "invalid hidden test output",
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                    },
                }
            )
        )
        return

    score = 0.0 if total == 0 else passed / total
    detail["stderr"] = proc.stderr.strip()
    print(json.dumps({"score": score, "detail": detail}))


if __name__ == "__main__":
    main()
