"""Exact linear solve for absorb_expect using Fraction arithmetic."""

import json
from fractions import Fraction


TRANSITIONS = {
    1: [(Fraction(1, 3), 1), (Fraction(2, 3), 0)],
    2: [(Fraction(1, 4), 2), (Fraction(1, 2), 1), (Fraction(1, 4), 0)],
    3: [(Fraction(1, 6), 3), (Fraction(1, 2), 2), (Fraction(1, 3), 1)],
    4: [(Fraction(1, 5), 4), (Fraction(2, 5), 3), (Fraction(2, 5), 2)],
    5: [(Fraction(1, 6), 5), (Fraction(1, 2), 4), (Fraction(1, 3), 3)],
    6: [(Fraction(1, 4), 6), (Fraction(1, 2), 5), (Fraction(1, 4), 4)],
}


def gaussian_elimination(matrix, rhs):
    size = len(matrix)
    for pivot_index in range(size):
        pivot_row = None
        for row_index in range(pivot_index, size):
            if matrix[row_index][pivot_index] != 0:
                pivot_row = row_index
                break
        if pivot_row is None:
            raise ValueError("singular system")
        if pivot_row != pivot_index:
            matrix[pivot_index], matrix[pivot_row] = matrix[pivot_row], matrix[pivot_index]
            rhs[pivot_index], rhs[pivot_row] = rhs[pivot_row], rhs[pivot_index]

        pivot = matrix[pivot_index][pivot_index]
        matrix[pivot_index] = [entry / pivot for entry in matrix[pivot_index]]
        rhs[pivot_index] /= pivot

        for row_index in range(size):
            if row_index == pivot_index:
                continue
            factor = matrix[row_index][pivot_index]
            if factor == 0:
                continue
            matrix[row_index] = [
                entry - factor * pivot_entry
                for entry, pivot_entry in zip(matrix[row_index], matrix[pivot_index])
            ]
            rhs[row_index] -= factor * rhs[pivot_index]
    return rhs


def solve_expectations():
    states = [1, 2, 3, 4, 5, 6]
    matrix = []
    rhs = []
    for state in states:
        row = []
        for other in states:
            coefficient = Fraction(1, 1) if state == other else Fraction(0, 1)
            for probability, destination in TRANSITIONS[state]:
                if destination == other:
                    coefficient -= probability
            row.append(coefficient)
        matrix.append(row)
        rhs.append(Fraction(state, 1))
    solved = gaussian_elimination(matrix, rhs)
    expectations = {0: Fraction(0, 1)}
    for state, value in zip(states, solved):
        expectations[state] = value
    return expectations


def serialize(expectations):
    return {
        "algorithm": "fraction_gaussian_elimination",
        "answer": str(expectations[6]),
        "state_expectations": {
            str(state): str(expectations[state]) for state in range(7)
        },
    }


def main():
    print(json.dumps(serialize(solve_expectations()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
