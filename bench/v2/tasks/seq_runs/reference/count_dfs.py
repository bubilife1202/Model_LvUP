import json


ALPHABET = range(1, 7)
LENGTH = 9
TARGET_SUM_MOD = 4
MODULUS = 9


def count_sequences():
    total = 0

    def dfs(position, last_symbol, second_last_symbol, run_length, sum_mod):
        nonlocal total
        if position == LENGTH:
            if sum_mod == TARGET_SUM_MOD:
                total += 1
            return

        for symbol in ALPHABET:
            if position > 0 and symbol == last_symbol and run_length == 2:
                continue
            if position >= 2 and second_last_symbol == 1 and last_symbol == 3 and symbol == 1:
                continue

            next_run_length = run_length + 1 if position > 0 and symbol == last_symbol else 1
            dfs(
                position + 1,
                symbol,
                last_symbol,
                next_run_length,
                (sum_mod + symbol) % MODULUS,
            )

    dfs(0, 0, 0, 0, 0)
    return total


def main():
    answer = count_sequences()
    print(json.dumps({"algorithm": "dfs_generator", "answer": answer}))


if __name__ == "__main__":
    main()
