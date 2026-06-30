from dataclasses import dataclass


ESCAPES = {
    "n": "\n",
    "t": "\t",
    "r": "\r",
    '"': '"',
    "\\": "\\",
}

SINGLE_OPS = set("+-*/()=<>!,")
DOUBLE_OPS = {"<=", ">=", "==", "!="}


@dataclass(frozen=True)
class Token:
    kind: str
    value: str
    line: int
    col: int


def tokenize(text):
    tokens = []
    i = 0
    line = 1
    col = 1
    n = len(text)

    def peek(offset=0):
        j = i + offset
        return text[j] if j < n else None

    def advance():
        nonlocal i, line, col
        ch = text[i]
        i += 1
        if ch == "\n":
            line += 1
            col = 1
        elif ch == "\t":
            col += 4
        else:
            col += 1
        return ch

    while i < n:
        ch = peek()
        if ch in " \t\r\n":
            advance()
            continue
        if ch == "#":
            while i < n and peek() != "\n":
                advance()
            continue

        start_line = line
        start_col = col
        pair = (ch or "") + (peek(1) or "")

        if pair in DOUBLE_OPS:
            advance()
            advance()
            tokens.append(Token("OP", pair, start_line, start_col))
            continue
        if ch in SINGLE_OPS:
            advance()
            tokens.append(Token("OP", ch, start_line, start_col))
            continue
        if ch.isalpha() or ch == "_":
            chars = [advance()]
            while i < n and (peek().isalnum() or peek() == "_"):
                chars.append(advance())
            tokens.append(Token("IDENT", "".join(chars), start_line, start_col))
            continue
        if ch.isdigit() or (ch == "." and (peek(1) or "").isdigit()):
            chars = []
            if ch == ".":
                chars.append(advance())
                while i < n and (peek() or "").isdigit():
                    chars.append(advance())
            else:
                while i < n and (peek() or "").isdigit():
                    chars.append(advance())
                if peek() == ".":
                    chars.append(advance())
                    while i < n and (peek() or "").isdigit():
                        chars.append(advance())
            tokens.append(Token("NUMBER", "".join(chars), start_line, start_col))
            continue
        if ch == '"':
            advance()
            chars = []
            closed = False
            while i < n:
                current = peek()
                if current == '"':
                    advance()
                    closed = True
                    break
                if current == "\\":
                    advance()
                    if i >= n:
                        chars.append("\\")
                        break
                    esc = advance()
                    chars.append(ESCAPES.get(esc, esc))
                    continue
                chars.append(advance())
            if not closed:
                raise SyntaxError(f"unterminated string at {start_line}:{start_col}")
            tokens.append(Token("STRING", "".join(chars), start_line, start_col))
            continue
        raise SyntaxError(f"unexpected character {ch!r} at {start_line}:{start_col}")

    return tokens
