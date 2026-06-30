import importlib.util
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
    here = Path(__file__).resolve().parent
    cases = json.loads((here / "hidden_cases.json").read_text(encoding="utf-8"))
    expected = json.loads((here / "hidden_expected.json").read_text(encoding="utf-8"))

    try:
        module = load_candidate(sys.argv[1])
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
