"""Digit-DP ground-truth program for digit_count."""

from functools import lru_cache


LIMIT = 7_654_321
DIGITS = tuple(int(ch) for ch in str(LIMIT))


@lru_cache(maxsize=None)
def count_valid(pos, tight, started, has_34, prev_is_3, digit_sum_mod_7):
    if pos == len(DIGITS):
        return 1 if started and has_34 and digit_sum_mod_7 == 0 else 0

    upper = DIGITS[pos] if tight else 9
    total = 0
    for digit in range(upper + 1):
        next_tight = tight and digit == upper
        if not started and digit == 0:
            total += count_valid(pos + 1, next_tight, False, False, False, 0)
            continue
        if digit == 5:
            continue
        total += count_valid(
            pos + 1,
            next_tight,
            True,
            has_34 or (prev_is_3 and digit == 4),
            digit == 3,
            (digit_sum_mod_7 + digit) % 7,
        )
    return total


def solve():
    return count_valid(0, True, False, False, False, 0)


if __name__ == "__main__":
    print(solve())
