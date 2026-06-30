import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GROUND_TRUTH_PATH = ROOT / "reference" / "ground_truth.json"
FINAL_ANSWER_RE = re.compile(r"^FINAL ANSWER:\s*([+-]?\d[\d,]*)\s*$")


def load_expected_answer():
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return int(payload["exact_answer"])


def extract_last_final_answer(text):
    matches = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = FINAL_ANSWER_RE.match(line)
        if match:
            matches.append(match.group(1))
    if not matches:
        raise ValueError("no line matched 'FINAL ANSWER: <integer>'")
    return int(matches[-1].replace(",", ""))


def score_answer(answer_path):
    expected = load_expected_answer()
    answer_text = Path(answer_path).read_text(encoding="utf-8")
    try:
        parsed = extract_last_final_answer(answer_text)
    except ValueError as exc:
        return {"score": 0.0, "detail": {"error": str(exc), "expected": expected}}

    score = 1.0 if parsed == expected else 0.0
    return {
        "score": score,
        "detail": {
            "parsed_answer": parsed,
            "expected_answer": expected,
            "is_exact_match": parsed == expected,
        },
    }


def main(argv):
    if len(argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "detail": {"error": "usage: python3 check.py <answer_file>"},
                }
            )
        )
        return 1
    print(json.dumps(score_answer(argv[1])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
