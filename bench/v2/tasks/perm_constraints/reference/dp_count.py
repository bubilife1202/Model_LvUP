import json
from functools import lru_cache


N = 9
TARGET_PARITY_MATCHES = 7
VALUES = tuple(range(1, N + 1))


@lru_cache(maxsize=None)
def count_states(position, used_mask, previous_value, parity_matches):
    if parity_matches > TARGET_PARITY_MATCHES:
        return 0
    if position > N:
        return 1 if parity_matches == TARGET_PARITY_MATCHES else 0

    remaining_positions = N - position + 1
    if parity_matches + remaining_positions < TARGET_PARITY_MATCHES:
        return 0

    total = 0
    position_parity = position % 2
    for value in VALUES:
        bit = 1 << (value - 1)
        if used_mask & bit:
            continue
        if value == position:
            continue
        if previous_value and abs(previous_value - value) == 1:
            continue
        total += count_states(
            position + 1,
            used_mask | bit,
            value,
            parity_matches + int((value % 2) == position_parity),
        )
    return total


def main():
    print(json.dumps({"answer": count_states(1, 0, 0, 0)}))


if __name__ == "__main__":
    main()
