"""Checker for absorb_expect."""

import json
import re
import sys
from fractions import Fraction
from pathlib import Path


HERE = Path(__file__).resolve().parent
GROUND_TRUTH = HERE / "reference" / "ground_truth.json"
FINAL_ANSWER_RE = re.compile(r"^\s*FINAL ANSWER:\s*(.*?)\s*$")
FRACTION_RE = re.compile(r"^[0-9]+/[0-9]+$")


def load_expected_answer():
    payload = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
    return payload["exact_answer"]


def extract_last_final_answer(text):
    last = None
    for line in text.splitlines():
        match = FINAL_ANSWER_RE.match(line)
        if match:
            last = match.group(1).strip()
    return last


def parse_reduced_fraction(text):
    if not FRACTION_RE.fullmatch(text):
        raise ValueError("expected a fraction in the form p/q")
    value = Fraction(text)
    if value.denominator <= 0:
        raise ValueError("denominator must be positive")
    canonical = f"{value.numerator}/{value.denominator}"
    if text != canonical:
        raise ValueError("fraction must already be reduced and canonical")
    return canonical


def score_answer(answer_file):
    expected = load_expected_answer()
    answer_text = Path(answer_file).read_text(encoding="utf-8")
    raw_final = extract_last_final_answer(answer_text)
    if raw_final is None:
        return {
            "score": 0.0,
            "detail": {
                "expected": expected,
                "found": None,
                "matched": False,
                "reason": "missing FINAL ANSWER line",
            },
        }

    try:
        candidate = parse_reduced_fraction(raw_final)
    except ValueError as exc:
        return {
            "score": 0.0,
            "detail": {
                "expected": expected,
                "found": raw_final,
                "matched": False,
                "reason": str(exc),
            },
        }

    matched = candidate == expected
    return {
        "score": 1.0 if matched else 0.0,
        "detail": {
            "expected": expected,
            "found": candidate,
            "matched": matched,
            "reason": "exact match" if matched else "wrong exact fraction",
        },
    }


def main(argv):
    if len(argv) != 2:
        raise SystemExit("usage: python3 check.py <answer_file>")
    print(json.dumps(score_answer(argv[1]), sort_keys=True))


if __name__ == "__main__":
    main(sys.argv)
