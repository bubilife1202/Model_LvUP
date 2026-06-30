import json
import pathlib
import re
import sys


# Limitations:
# This checker is intentionally approximate. It matches review findings to
# seeded defects using case-insensitive regex conjunctions, not semantic
# understanding. Good paraphrases can be missed, and a vague finding can
# occasionally overmatch if it contains several seed keywords together.
# To reduce false positives, matching is done per numbered finding block and
# each seed requires all regexes in one alternative set. This is still recall-
# oriented scoring, not proof that the model truly understood the bug.


def load_seeds():
    here = pathlib.Path(__file__).resolve().parent
    return json.loads((here / "reference" / "seeds.json").read_text(encoding="utf-8"))


def split_findings(text):
    parts = re.split(r"(?m)^\s*\d+\.\s+", text.strip())
    findings = [part.strip() for part in parts if part.strip()]
    return findings or [text.strip()]


def finding_matches(block, alternative):
    return all(re.search(pattern, block, re.I | re.S) for pattern in alternative)


def score_text(text):
    findings = split_findings(text)
    matched = []
    unmatched = []
    for seed in load_seeds():
        if any(
            finding_matches(block, alternative)
            for block in findings
            for alternative in seed["signatures"]
        ):
            matched.append(seed["id"])
        else:
            unmatched.append(seed["id"])
    score = len(matched) / 12.0
    return {
        "score": score,
        "detail": {
            "matched": matched,
            "unmatched": unmatched,
            "finding_count": len(findings),
        },
    }


if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        print(json.dumps(score_text(handle.read())))
