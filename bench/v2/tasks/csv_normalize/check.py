import json
import pathlib
import sys


def load_lines(path):
    return pathlib.Path(path).read_text(encoding="utf-8").splitlines()


def score_lines(expected, got):
    total = max(len(expected), len(got))
    if total == 0:
        return 0.0, []
    mismatches = []
    matches = 0
    for idx in range(total):
        expected_line = expected[idx] if idx < len(expected) else None
        got_line = got[idx] if idx < len(got) else None
        if expected_line == got_line:
            matches += 1
        else:
            mismatches.append(
                {
                    "line": idx + 1,
                    "expected": expected_line,
                    "got": got_line,
                }
            )
    return matches / total, mismatches


def main():
    here = pathlib.Path(__file__).resolve().parent
    expected = load_lines(here / "reference" / "answer.csv")
    got = load_lines(sys.argv[1])
    score, mismatches = score_lines(expected, got)
    print(
        json.dumps(
            {
                "score": score,
                "detail": {
                    "expected_lines": len(expected),
                    "got_lines": len(got),
                    "mismatches": mismatches[:10],
                },
            }
        )
    )


if __name__ == "__main__":
    main()
