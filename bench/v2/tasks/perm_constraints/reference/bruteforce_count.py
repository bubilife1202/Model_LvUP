import itertools
import json


VALUES = tuple(range(1, 10))


def count_permutations():
    total = 0
    for perm in itertools.permutations(VALUES):
        if any(value == index for index, value in enumerate(perm, start=1)):
            continue
        if any(abs(perm[i] - perm[i + 1]) == 1 for i in range(len(perm) - 1)):
            continue
        parity_matches = sum((value % 2) == (index % 2) for index, value in enumerate(perm, start=1))
        if parity_matches == 7:
            total += 1
    return total


def main():
    print(json.dumps({"answer": count_permutations()}))


if __name__ == "__main__":
    main()
