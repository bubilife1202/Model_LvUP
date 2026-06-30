"""Direct-enumeration ground-truth program for digit_count."""


LIMIT = 7_654_321


def qualifies(n):
    text = str(n)
    if "5" in text:
        return False
    if "34" not in text:
        return False
    return sum(int(ch) for ch in text) % 7 == 0


def solve():
    total = 0
    for value in range(1, LIMIT + 1):
        if qualifies(value):
            total += 1
    return total


if __name__ == "__main__":
    print(solve())
