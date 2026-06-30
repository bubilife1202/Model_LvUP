import json
from pathlib import Path

from tokenizer import Token, tokenize


def serialize(tokens):
    return [
        {"kind": token.kind, "value": token.value, "line": token.line, "col": token.col}
        for token in tokens
    ]


def build_cases():
    return [
        {"name": "integer", "src": "42"},
        {"name": "decimal-basic", "src": "12.34"},
        {"name": "leading-dot-decimal", "src": ".5 + 1"},
        {"name": "trailing-dot-decimal", "src": "7."},
        {"name": "lone-dot-error", "src": "."},
        {"name": "number-then-ident", "src": "12abc"},
        {"name": "identifier", "src": "_name12"},
        {"name": "single-ops", "src": "+-*/()=<>!,"},
        {"name": "double-ops", "src": "<= >= == !="},
        {"name": "lookahead-order", "src": "a<==b"},
        {"name": "comment-middle", "src": "x# comment\ny"},
        {"name": "comment-eof", "src": "x # trailing"},
        {"name": "comment-only-eof", "src": "# trailing"},
        {"name": "string-basic", "src": '"hi"'},
        {"name": "string-escapes", "src": '"a\\\\b\\n\\t\\r\\\""'},
        {"name": "string-hash", "src": '"#not comment"'},
        {"name": "string-unknown-escape", "src": '"a\\qb"'},
        {"name": "string-newline", "src": '"a\nb" c'},
        {"name": "string-newline-double", "src": '"a\nb\nc"\n+'},
        {"name": "tab-column", "src": "\tname"},
        {"name": "tab-then-op", "src": "\t!="},
        {"name": "tabs-and-newline", "src": "\tfoo\n\tbar"},
        {"name": "mixed-program", "src": 'sum<=.5 # c\n"value"!=x'},
        {"name": "unexpected-char", "src": "@"},
        {"name": "unterminated-escape", "src": '"abc\\'},
        {"name": "unterminated-string", "src": '"abc'},
    ]


def evaluate_case(case):
    try:
        return {"tokens": serialize(tokenize(case["src"]))}
    except Exception as exc:
        return {"error": {"type": type(exc).__name__, "message": str(exc)}}


def main():
    here = Path(__file__).resolve().parent
    cases = build_cases()
    expected = {case["name"]: evaluate_case(case) for case in cases}
    (here / "hidden_cases.json").write_text(
        json.dumps(cases, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    (here / "hidden_expected.json").write_text(
        json.dumps(expected, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
