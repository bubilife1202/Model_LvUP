import json
import re
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
GROUND_TRUTH_PATH = HERE / "reference" / "ground_truth.json"
FINAL_ANSWER_RE = re.compile(r"^\s*FINAL ANSWER:\s*([+-]?\d[\d,]*)\s*$")


def _load_ground_truth():
    payload = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    return int(payload["answer"])


def _parse_last_final_answer(text):
    last_final_line = None
    parsed_value = None
    for line in text.splitlines():
        if "FINAL ANSWER:" not in line:
            continue
        last_final_line = line
        match = FINAL_ANSWER_RE.match(line)
        if match is None:
            parsed_value = None
            continue
        parsed_value = int(match.group(1).replace(",", ""))
    return last_final_line, parsed_value


def score_answer(answer_path):
    expected = _load_ground_truth()
    answer_text = Path(answer_path).read_text(encoding="utf-8")
    last_final_line, parsed_value = _parse_last_final_answer(answer_text)
    if last_final_line is None:
        return {
            "score": 0.0,
            "detail": {
                "error": "missing_final_answer_line",
                "expected": expected,
            },
        }
    if parsed_value is None:
        return {
            "score": 0.0,
            "detail": {
                "error": "malformed_final_answer_line",
                "expected": expected,
                "last_final_answer_line": last_final_line,
            },
        }
    is_correct = parsed_value == expected
    return {
        "score": 1.0 if is_correct else 0.0,
        "detail": {
            "expected": expected,
            "parsed": parsed_value,
            "is_correct": is_correct,
            "last_final_answer_line": last_final_line,
        },
    }


def main(argv):
    if len(argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "detail": {
                        "error": "usage",
                        "message": "usage: python3 check.py <answer_file>",
                    },
                }
            )
        )
        return 1
    try:
        result = score_answer(argv[1])
    except FileNotFoundError as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "detail": {
                        "error": "file_not_found",
                        "message": str(exc),
                    },
                }
            )
        )
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
