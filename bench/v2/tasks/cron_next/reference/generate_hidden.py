import json
from pathlib import Path

from oracle_enumerate import next_fire as enum_next_fire
from oracle_fieldwise import next_fire as field_next_fire


CASES = [
    {"cron_expr": "* * * * *", "after_iso": "2024-01-01T00:00:00Z"},
    {"cron_expr": "*/15 * * * *", "after_iso": "2024-01-01T00:14:00Z"},
    {"cron_expr": "*/15 * * * *", "after_iso": "2024-01-01T00:15:00Z"},
    {"cron_expr": "58-59/1 * * * *", "after_iso": "2024-01-01T00:58:00Z"},
    {"cron_expr": "58-59/1 * * * *", "after_iso": "2024-01-01T00:59:00Z"},
    {"cron_expr": "0 0 1 * *", "after_iso": "2024-01-31T23:59:00Z"},
    {"cron_expr": "0 0 29 2 *", "after_iso": "2023-02-28T23:59:00Z"},
    {"cron_expr": "0 0 29 2 *", "after_iso": "2024-02-29T00:00:00Z"},
    {"cron_expr": "0 0 31 * *", "after_iso": "2024-04-01T00:00:00Z"},
    {"cron_expr": "0 0 * 2 0", "after_iso": "2024-02-28T23:59:00Z"},
    {"cron_expr": "0 9 * * 1-5", "after_iso": "2024-03-01T09:00:00Z"},
    {"cron_expr": "30 14 1 * 1", "after_iso": "2024-01-01T14:30:00Z"},
    {"cron_expr": "30 14 1 * 1", "after_iso": "2024-01-31T14:30:00Z"},
    {"cron_expr": "0 0 13 * 5", "after_iso": "2024-09-12T23:59:00Z"},
    {"cron_expr": "0 0 13 * 5", "after_iso": "2024-09-13T00:00:00Z"},
    {"cron_expr": "0 12 10-20/5 6,12 *", "after_iso": "2024-06-14T12:00:00Z"},
    {"cron_expr": "0 12 10-20/5 6,12 *", "after_iso": "2024-06-20T12:00:00Z"},
    {"cron_expr": "5 4 * * 0,6", "after_iso": "2024-06-07T04:05:00Z"},
    {"cron_expr": "0 */6 * * *", "after_iso": "2024-06-01T18:00:00Z"},
    {"cron_expr": "7 3 1 1 *", "after_iso": "2024-12-31T23:59:00Z"},
    {"cron_expr": "0 0 * * *", "after_iso": "2024-01-01T00:00:59Z"},
    {"cron_expr": "* 23 * * *", "after_iso": "2024-01-01T23:59:00Z"},
    {"cron_expr": "0 0 * 12 0", "after_iso": "2024-12-29T00:00:00Z"},
    {"cron_expr": "0 0 31 1,3,5,7,8,10,12 *", "after_iso": "2024-08-31T00:00:00Z"},
    {"cron_expr": "*/20 1-5/2 * * *", "after_iso": "2024-06-01T03:40:00Z"},
    {"cron_expr": "1,13,37 0 * * *", "after_iso": "2024-06-01T00:13:00Z"},
    {"cron_expr": "0 0 1 3 0", "after_iso": "2025-02-28T23:59:00Z"},
    {"cron_expr": "0 0 1 3 0", "after_iso": "2025-03-01T00:00:00Z"},
    {"cron_expr": "15 8 28-31 * 1-3", "after_iso": "2024-02-27T08:15:00Z"},
    {"cron_expr": "15 8 28-31 * 1-3", "after_iso": "2024-02-29T08:15:00Z"},
    {"cron_expr": "0 0 * * 2", "after_iso": "2024-02-27T00:00:00Z"},
    {"cron_expr": "59 23 31 12 *", "after_iso": "2024-12-31T23:58:00Z"},
    {"cron_expr": "59 23 31 12 *", "after_iso": "2024-12-31T23:59:00Z"},
    {"cron_expr": "0 0 29 2 4", "after_iso": "2024-02-28T23:59:00Z"},
    {"cron_expr": "0 0 29 2 4", "after_iso": "2024-02-29T00:00:00Z"},
    {"cron_expr": "0 0 29 2 *", "after_iso": "1999-02-28T23:59:00Z"},
    {"cron_expr": "0 0 29 2 *", "after_iso": "2096-02-29T00:00:00Z"}
]


def main():
    frozen = []
    for case in CASES:
        expected_a = enum_next_fire(case["cron_expr"], case["after_iso"])
        expected_b = field_next_fire(case["cron_expr"], case["after_iso"])
        if expected_a != expected_b:
            raise AssertionError(f"oracle mismatch for {case}: {expected_a} != {expected_b}")
        frozen.append(
            {
                "cron_expr": case["cron_expr"],
                "after_iso": case["after_iso"],
                "expected": expected_a,
            }
        )

    output_path = Path(__file__).resolve().parent.parent / "hidden_tests.json"
    output_path.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(frozen)} hidden tests to {output_path}")


if __name__ == "__main__":
    main()
