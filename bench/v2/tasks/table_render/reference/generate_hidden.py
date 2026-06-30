import json
from pathlib import Path

from oracle_primary import render_table as render_primary
from oracle_secondary import render_table as render_secondary


CASES = [
    {"name": "basic_left", "rows": [["a", "bb"]], "widths": [3, 4], "aligns": ["l", "l"]},
    {"name": "basic_right", "rows": [["7", "42"]], "widths": [3, 4], "aligns": ["r", "r"]},
    {"name": "center_odd_padding", "rows": [["xx"]], "widths": [5], "aligns": ["c"]},
    {"name": "empty_cell", "rows": [["", "x"]], "widths": [3, 2], "aligns": ["l", "l"]},
    {"name": "exact_fit_word", "rows": [["tool"]], "widths": [4], "aligns": ["l"]},
    {"name": "wrap_spaces_greedy", "rows": [["a bb ccc d"]], "widths": [6], "aligns": ["l"]},
    {"name": "hard_break_long_word", "rows": [["encyclopedia"]], "widths": [4], "aligns": ["l"]},
    {"name": "single_char_width", "rows": [["abcd"]], "widths": [1], "aligns": ["l"]},
    {"name": "ellipsis_width_two", "rows": [["a b c d"]], "widths": [2], "aligns": ["l"]},
    {"name": "ellipsis_width_five", "rows": [["aa bb cc dd ee"]], "widths": [5], "aligns": ["l"]},
    {"name": "mixed_row_height", "rows": [["short", "a bb ccc d"]], "widths": [5, 6], "aligns": ["l", "l"]},
    {"name": "two_rows_separator", "rows": [["a"], ["b"]], "widths": [1], "aligns": ["l"]},
    {"name": "mixed_aligns", "rows": [["x", "y", "z"]], "widths": [3, 3, 4], "aligns": ["l", "r", "c"]},
    {"name": "empty_table", "rows": [], "widths": [2, 1], "aligns": ["l", "r"]},
    {"name": "empty_with_tall_neighbor", "rows": [["", "alpha beta gamma delta"]], "widths": [4, 5], "aligns": ["c", "l"]},
    {"name": "exact_three_lines", "rows": [["ab cd ef"]], "widths": [2], "aligns": ["l"]},
    {"name": "four_lines_truncate", "rows": [["ab cd ef gh"]], "widths": [2], "aligns": ["l"]},
    {"name": "flush_before_long_word", "rows": [["a abcdefghij z"]], "widths": [4], "aligns": ["l"]},
    {"name": "collapse_multi_spaces", "rows": [["a  b   c"]], "widths": [3], "aligns": ["l"]},
    {"name": "unicode_len_semantics", "rows": [["가나", "ééé"]], "widths": [3, 4], "aligns": ["c", "r"]},
    {"name": "center_even_padding", "rows": [["q"]], "widths": [4], "aligns": ["c"]},
    {"name": "single_char_multirow", "rows": [["a", "b"], ["", "cc"]], "widths": [1, 1], "aligns": ["c", "r"]},
    {"name": "wrap_hardbreak_truncate", "rows": [["ab cdefghijk lm nop"]], "widths": [3], "aligns": ["l"]},
    {"name": "all_empty_cells", "rows": [["", ""], ["", ""]], "widths": [2, 3], "aligns": ["r", "c"]},
    {"name": "center_width_one", "rows": [["x"]], "widths": [1], "aligns": ["c"]},
    {"name": "right_align_shorter_tail", "rows": [["aa bb", "z"]], "widths": [3, 3], "aligns": ["l", "r"]},
    {"name": "ellipsis_from_hard_break", "rows": [["abcdefghij"]], "widths": [2], "aligns": ["l"]},
    {"name": "three_columns_varied_heights", "rows": [["a bb", "ccc d e", "fffff"]], "widths": [3, 3, 2], "aligns": ["l", "c", "r"]},
    {"name": "exact_border_sample", "rows": [["ab", "c", "def"]], "widths": [3, 1, 4], "aligns": ["l", "r", "c"]},
    {"name": "hard_break_not_merged_after", "rows": [["abcdefgh ij"]], "widths": [3], "aligns": ["l"]},
]


def main():
    task_dir = Path(__file__).resolve().parent.parent
    expected = {}
    for case in CASES:
        primary = render_primary(case["rows"], case["widths"], case["aligns"])
        secondary = render_secondary(case["rows"], case["widths"], case["aligns"])
        if primary != secondary:
            raise AssertionError("oracle mismatch for %s" % case["name"])
        expected[case["name"]] = primary
    (task_dir / "hidden_cases.json").write_text(
        json.dumps(CASES, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (task_dir / "hidden_expected.json").write_text(
        json.dumps(expected, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
