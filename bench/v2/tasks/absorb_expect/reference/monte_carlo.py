"""Monte Carlo sanity check for absorb_expect."""

import json
import random
from fractions import Fraction


SEED = 20260612
TRIALS = 200000
EXACT = Fraction(9479, 450)


def next_state(state, rng):
    if state == 6:
        draw = rng.randrange(4)
        return 6 if draw == 0 else 5 if draw in (1, 2) else 4
    if state == 5:
        draw = rng.randrange(6)
        return 5 if draw == 0 else 4 if draw in (1, 2, 3) else 3
    if state == 4:
        draw = rng.randrange(5)
        return 4 if draw == 0 else 3 if draw in (1, 2) else 2
    if state == 3:
        draw = rng.randrange(6)
        return 3 if draw == 0 else 2 if draw in (1, 2, 3) else 1
    if state == 2:
        draw = rng.randrange(4)
        return 2 if draw == 0 else 1 if draw in (1, 2) else 0
    if state == 1:
        draw = rng.randrange(3)
        return 1 if draw == 0 else 0
    return 0


def run_trial(rng):
    state = 6
    total_cost = 0
    while state != 0:
        total_cost += state
        state = next_state(state, rng)
    return total_cost


def main():
    rng = random.Random(SEED)
    total = 0
    for _ in range(TRIALS):
        total += run_trial(rng)
    estimate = total / TRIALS
    exact_value = EXACT.numerator / EXACT.denominator
    output = {
        "algorithm": "fixed_seed_monte_carlo_guard",
        "trials": TRIALS,
        "seed": SEED,
        "estimate": estimate,
        "exact_value": exact_value,
        "absolute_error": abs(estimate - exact_value),
        "note": "Sanity check only; not a proof.",
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
