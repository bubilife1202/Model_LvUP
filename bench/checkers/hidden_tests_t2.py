"""Hidden tests for T2. Usage: python3 hidden_tests_t2.py <candidate_module.py>
Prints JSON: {"passed": k, "total": n, "failures": [...]}

Each case targets the spec; cases are tagged with the seeded bug they catch
(A ban-boundary, B capacity, C prune-boundary, D banned-call-recorded)."""
import importlib.util
import json
import sys


def build_cases():
    cases = []

    def case(name, fn):
        cases.append((name, fn))

    def c_new_identity(RW):
        rw = RW(2, 10)
        assert rw.allow("a", 0.0) is True, "first call must be allowed"
    case("new-identity-allowed", c_new_identity)

    def c_capacity(RW):  # catches B
        rw = RW(2, 10)
        assert rw.allow("a", 0.0) is True
        assert rw.allow("a", 0.5) is True
        assert rw.allow("a", 0.6) is False, "3rd call within window must be refused (limit=2)"
    case("capacity-limit", c_capacity)

    def c_refused_not_recorded(RW):
        rw = RW(2, 10)
        assert rw.allow("a", 0.0) is True
        assert rw.allow("a", 0.5) is True
        assert rw.allow("a", 0.6) is False
        assert rw.allow("a", 0.7) is False
        # window at 10.4 is (0.4, 10.4]: ts 0.0 out, ts 0.5 in -> 1 recorded -> allow
        assert rw.allow("a", 10.4) is True, "refused calls must not be recorded"
    case("refused-not-recorded", c_refused_not_recorded)

    def c_prune_boundary(RW):  # catches C
        rw = RW(1, 10)
        assert rw.allow("b", 0.0) is True
        assert rw.allow("b", 10.0) is True, \
            "call at exactly now-window is outside the half-open window"
    case("prune-boundary", c_prune_boundary)

    def c_ban_boundary(RW):  # catches A
        rw = RW(5, 10)
        rw.ban("c", 10.0)
        assert rw.allow("c", 9.99) is False, "banned strictly before until"
        assert rw.allow("c", 10.0) is True, "ban expires AT until"
    case("ban-boundary", c_ban_boundary)

    def c_banned_not_recorded(RW):  # catches D
        rw = RW(1, 100)
        rw.ban("d", 10.0)
        assert rw.allow("d", 5.0) is False
        assert rw.allow("d", 11.0) is True, "refused-while-banned call must not be recorded"
    case("banned-not-recorded", c_banned_not_recorded)

    def c_ban_never_raise(RW):
        rw = RW(1, 10)
        rw.ban("e", 5.0)
        assert rw.allow("e", 6.0) is True
    case("ban-then-new-identity", c_ban_never_raise)

    def c_sliding(RW):
        rw = RW(3, 5)
        assert rw.allow("f", 0.0) is True
        assert rw.allow("f", 1.0) is True
        assert rw.allow("f", 2.0) is True
        assert rw.allow("f", 3.0) is False
        # at 5.1: window (0.1, 5.1]; ts 0.0 pruned; 1.0,2.0 remain -> allow
        assert rw.allow("f", 5.1) is True
    case("sliding-regression", c_sliding)

    def c_still_banned(RW):
        rw = RW(5, 10)
        rw.ban("g", 100.0)
        assert rw.allow("g", 50.0) is False
    case("still-banned", c_still_banned)

    def c_independent(RW):
        rw = RW(1, 10)
        assert rw.allow("h1", 0.0) is True
        assert rw.allow("h2", 0.0) is True, "identities must be independent"
        assert rw.allow("h1", 1.0) is False
    case("identities-independent", c_independent)

    return cases


def main():
    cand_path = sys.argv[1]
    cases = build_cases()
    failures = []
    passed = 0
    try:
        spec = importlib.util.spec_from_file_location("candidate_t2", cand_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        RW = getattr(mod, "RateWindow")
    except Exception as e:
        print(json.dumps({"passed": 0, "total": len(cases),
                          "failures": [f"import error: {e!r}"]}))
        return

    for name, fn in cases:
        try:
            fn(RW)
            passed += 1
        except AssertionError as e:
            failures.append(f"{name}: {e}")
        except Exception as e:
            failures.append(f"{name}: raised {e!r}")

    print(json.dumps({"passed": passed, "total": len(cases), "failures": failures}))


if __name__ == "__main__":
    main()
