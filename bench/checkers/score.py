"""Unified scorer for LvUP-Bench objective tasks.

Usage: python3 score.py <task_id> <answer_file>
Prints JSON: {"task": ..., "score": float in [0,1], "detail": {...}}

task_id in {T1_intervalset, T2_ratewindow, T3_M1_digits, T3_M2_binary, T4_constraints}
"""
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ANSWERS = {"T3_M1_digits": "293749", "T3_M2_binary": "324288"}


def extract_code(text):
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, flags=re.S)
    if blocks:
        return blocks[-1]
    # fallback: maybe raw code without fences
    if "class " in text or "def " in text:
        return text
    return None


def run_hidden(test_script, code):
    with tempfile.TemporaryDirectory() as td:
        cand = os.path.join(td, "candidate.py")
        with open(cand, "w") as f:
            f.write(code)
        try:
            out = subprocess.run(
                [sys.executable, os.path.join(HERE, test_script), cand],
                capture_output=True, text=True, timeout=60,
            )
            return json.loads(out.stdout.strip())
        except subprocess.TimeoutExpired:
            return {"passed": 0, "total": 1, "failures": ["timeout"]}
        except Exception as e:
            return {"passed": 0, "total": 1, "failures": [f"runner error: {e!r}"]}


def main():
    task, path = sys.argv[1], sys.argv[2]
    with open(path) as f:
        text = f.read()

    if task in ("T1_intervalset", "T2_ratewindow"):
        code = extract_code(text)
        if code is None:
            result = {"passed": 0, "total": 1, "failures": ["no code block found"]}
        else:
            script = "hidden_tests_t1.py" if task == "T1_intervalset" else "hidden_tests_t2.py"
            result = run_hidden(script, code)
        score = result["passed"] / max(result["total"], 1)
    elif task in ANSWERS:
        m = re.findall(r"FINAL ANSWER:\s*\$?\\?(?:boxed\{)?([\d,]+)", text)
        if not m:  # fallback: last integer-looking token on a 'final'-ish line
            m = re.findall(r"([\d,]{3,})\s*$", text.strip())
        got = m[-1].replace(",", "") if m else None
        ok = got == ANSWERS[task]
        score = 1.0 if ok else 0.0
        result = {"got": got, "expected": ANSWERS[task]}
    elif task == "T4_constraints":
        sys.path.insert(0, HERE)
        from check_t4 import check
        result = check(text)
        score = result["passed"] / result["total"]
    else:
        raise SystemExit(f"unknown task {task}")

    print(json.dumps({"task": task, "score": round(score, 4), "detail": result}))


if __name__ == "__main__":
    main()
