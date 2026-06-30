"""Ground-truth computation for LvUP-Bench math tasks M1, M2.

Each answer is computed two independent ways (brute force + DP).
The script asserts agreement and prints the verified answers.
"""
from itertools import product


# ---------- M1 ----------
# Count length-7 strings over digits 0..9 (leading zeros allowed) with
# digit sum exactly 30 and no two adjacent digits equal.

def m1_brute() -> int:
    count = 0
    # depth-first with pruning to keep runtime reasonable
    def rec(pos: int, prev: int, s: int) -> None:
        nonlocal count
        if s > 30:
            return
        remaining = 7 - pos
        if s + 9 * remaining < 30:
            return
        if pos == 7:
            if s == 30:
                count += 1
            return
        for d in range(10):
            if d != prev:
                rec(pos + 1, d, s + d)
    rec(0, -1, 0)
    return count


def m1_dp() -> int:
    # dp[d][s] = number of prefixes ending in digit d with sum s
    dp = [[0] * 31 for _ in range(10)]
    for d in range(10):
        if d <= 30:
            dp[d][d] = 1
    for _ in range(6):
        ndp = [[0] * 31 for _ in range(10)]
        for d in range(10):
            for s in range(31):
                if dp[d][s] == 0:
                    continue
                for nd in range(10):
                    if nd != d and s + nd <= 30:
                        ndp[nd][s + nd] += dp[d][s]
        dp = ndp
    return sum(dp[d][30] for d in range(10))


# ---------- M2 ----------
# Count binary strings of length 20 that do NOT contain "0110" as a
# (contiguous) substring.

def m2_brute() -> int:
    bad = "0110"
    count = 0
    for bits in product("01", repeat=20):
        if bad not in "".join(bits):
            count += 1
    return count


def m2_dp() -> int:
    # KMP-automaton DP over pattern "0110"; states 0..3 = chars matched
    pat = "0110"
    # build failure links
    fail = [0] * len(pat)
    k = 0
    for i in range(1, len(pat)):
        while k > 0 and pat[i] != pat[k]:
            k = fail[k - 1]
        if pat[i] == pat[k]:
            k += 1
        fail[i] = k

    def step(state: int, c: str) -> int:
        while state > 0 and pat[state] != c:
            state = fail[state - 1]
        if pat[state] == c:
            state += 1
        return state

    dp = {0: 1}
    for _ in range(20):
        ndp = {}
        for st, cnt in dp.items():
            for c in "01":
                ns = step(st, c)
                if ns == len(pat):
                    continue  # pattern completed -> excluded
                ndp[ns] = ndp.get(ns, 0) + cnt
        dp = ndp
    return sum(dp.values())


if __name__ == "__main__":
    a1, b1 = m1_brute(), m1_dp()
    assert a1 == b1, f"M1 mismatch: brute={a1} dp={b1}"
    a2, b2 = m2_brute(), m2_dp()
    assert a2 == b2, f"M2 mismatch: brute={a2} dp={b2}"
    print(f"M1 (len-7 digit strings, sum 30, no equal adjacent): {a1}")
    print(f"M2 (len-20 binary strings avoiding '0110'):          {a2}")
