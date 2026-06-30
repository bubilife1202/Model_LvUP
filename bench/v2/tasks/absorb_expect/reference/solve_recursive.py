"""Exact first-step analysis for absorb_expect using memoized back-substitution."""

import json
from fractions import Fraction
from functools import lru_cache


TRANSITIONS = {
    0: [],
    1: [(Fraction(1, 3), 1), (Fraction(2, 3), 0)],
    2: [(Fraction(1, 4), 2), (Fraction(1, 2), 1), (Fraction(1, 4), 0)],
    3: [(Fraction(1, 6), 3), (Fraction(1, 2), 2), (Fraction(1, 3), 1)],
    4: [(Fraction(1, 5), 4), (Fraction(2, 5), 3), (Fraction(2, 5), 2)],
    5: [(Fraction(1, 6), 5), (Fraction(1, 2), 4), (Fraction(1, 3), 3)],
    6: [(Fraction(1, 4), 6), (Fraction(1, 2), 5), (Fraction(1, 4), 4)],
}


@lru_cache(maxsize=None)
def expectation(state):
    if state == 0:
        return Fraction(0, 1)
    stay_probability = Fraction(0, 1)
    lower_contribution = Fraction(0, 1)
    for probability, destination in TRANSITIONS[state]:
        if destination == state:
            stay_probability += probability
        else:
            lower_contribution += probability * expectation(destination)
    return (Fraction(state, 1) + lower_contribution) / (Fraction(1, 1) - stay_probability)


def solve_expectations():
    return {state: expectation(state) for state in range(7)}


def serialize(expectations):
    return {
        "algorithm": "memoized_first_step_back_substitution",
        "answer": str(expectations[6]),
        "state_expectations": {
            str(state): str(expectations[state]) for state in range(7)
        },
    }


def main():
    print(json.dumps(serialize(solve_expectations()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
