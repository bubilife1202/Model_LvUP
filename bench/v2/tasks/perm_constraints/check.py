import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GROUND_TRUTH_PATH = ROOT / "reference" / "ground_truth.json"
FINAL_ANSWER_RE = re.compile(r"^\s*FINAL ANSWER:\s*([+-]?[0-9][0-9,]*)\s*$")


def load_expected_answer():
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return int(payload["answer"])


def parse_last_final_answer(answer_text):
    last_match = None
    for line in answer_text.splitlines():
        match = FINAL_ANSWER_RE.match(line)
        if match:
            last_match = match.group(1)
    if last_match is None:
        raise ValueError("answer must contain a line of the form 'FINAL ANSWER: <integer>'")
    return int(last_match.replace(",", ""))


def score_answer(answer_path):
    try:
        actual = parse_last_final_answer(answer_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"score": 0.0, "detail": {"error": f"answer file not found: {answer_path}"}}
    except ValueError as exc:
        return {"score": 0.0, "detail": {"error": str(exc)}}

    expected = load_expected_answer()
    correct = actual == expected
    return {
        "score": 1.0 if correct else 0.0,
        "detail": {
            "expected_answer": expected,
            "parsed_answer": actual,
            "correct": correct,
        },
    }


def main(argv):
    if len(argv) != 2:
        print(json.dumps({"score": 0.0, "detail": {"error": "usage: python3 check.py <answer_file>"}}))
        return 1
    result = score_answer(Path(argv[1]))
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
