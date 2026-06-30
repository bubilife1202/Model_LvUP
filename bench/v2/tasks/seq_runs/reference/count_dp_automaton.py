import json
from collections import Counter


ALPHABET = range(1, 7)
LENGTH = 9
TARGET_SUM_MOD = 4
MODULUS = 9


def advance_pattern_state(pattern_state, symbol):
    if pattern_state == 0:
        return 1 if symbol == 1 else 0
    if pattern_state == 1:
        if symbol == 3:
            return 2
        return 1 if symbol == 1 else 0
    if pattern_state == 2:
        if symbol == 1:
            return None
        return 0
    raise ValueError(f"unexpected pattern_state={pattern_state}")


def build_transition_map():
    transitions = {}
    initial_state = (0, 0, 0, 0)
    frontier = [initial_state]
    seen = {initial_state}

    while frontier:
        state = frontier.pop()
        last_symbol, run_length, pattern_state, sum_mod = state
        next_states = []
        for symbol in ALPHABET:
            if symbol == last_symbol and run_length == 2:
                continue
            next_pattern_state = advance_pattern_state(pattern_state, symbol)
            if next_pattern_state is None:
                continue
            next_run_length = run_length + 1 if symbol == last_symbol else 1
            next_state = (
                symbol,
                next_run_length,
                next_pattern_state,
                (sum_mod + symbol) % MODULUS,
            )
            next_states.append(next_state)
            if next_state not in seen:
                seen.add(next_state)
                frontier.append(next_state)
        transitions[state] = next_states
    return transitions


def count_sequences():
    transitions = build_transition_map()
    counts = Counter({(0, 0, 0, 0): 1})

    for _ in range(LENGTH):
        next_counts = Counter()
        for state, ways in counts.items():
            for next_state in transitions[state]:
                next_counts[next_state] += ways
        counts = next_counts

    return sum(ways for state, ways in counts.items() if state[3] == TARGET_SUM_MOD)


def main():
    answer = count_sequences()
    print(json.dumps({"algorithm": "dp_automaton", "answer": answer}))


if __name__ == "__main__":
    main()
