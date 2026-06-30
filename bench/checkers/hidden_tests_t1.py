"""Hidden tests for T1. Usage: python3 hidden_tests_t1.py <candidate_module.py>
Prints JSON: {"passed": k, "total": n, "failures": [...]}"""
import importlib.util
import json
import os
import sys


def main():
    cand_path = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "t1_cases.json")) as f:
        cases = json.load(f)

    failures = []
    passed = 0
    try:
        spec = importlib.util.spec_from_file_location("candidate_t1", cand_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, "IntervalSet")
    except Exception as e:  # import error -> everything fails
        print(json.dumps({"passed": 0, "total": len(cases),
                          "failures": [f"import error: {e!r}"]}))
        return

    for case in cases:
        try:
            s = cls()
            for op, lo, hi, lc, hc in case["ops"]:
                getattr(s, op)(lo, hi, lc, hc)
            ok = True
            for kind, arg, expected in case["checks"]:
                got = s.canonical() if kind == "canonical" else s.contains(arg)
                if got != expected:
                    ok = False
                    failures.append(
                        f"{case['name']}: {kind}({arg}) -> {got!r}, expected {expected!r}")
                    break
            if ok:
                passed += 1
        except Exception as e:
            failures.append(f"{case['name']}: raised {e!r}")

    print(json.dumps({"passed": passed, "total": len(cases), "failures": failures}))


if __name__ == "__main__":
    main()
