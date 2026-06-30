import datetime as dt
import decimal
import pathlib
import re


RAW_HEADERS = ["Note", "Score", "Joined", "Name", "Active", "Age", "ID", "Alias", "City"]
RENAME_MAP = {
    "Note": "note",
    "Score": "score",
    "Joined": "joined_date",
    "Name": "full_name",
    "Active": "active",
    "Age": "age",
    "ID": "id",
    "Alias": "nickname",
    "City": "city",
}
OUTPUT_HEADERS = [
    "id",
    "full_name",
    "nickname",
    "age",
    "score",
    "active",
    "joined_date",
    "city",
    "note",
]
NULL_TOKENS = {"", "null", "nil", "n/a", "na"}
BOOL_MAP = {
    "true": True,
    "false": False,
    "yes": True,
    "no": False,
    "1": True,
    "0": False,
}
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y")


def parse_line(line):
    fields = []
    i = 0
    length = len(line)
    while True:
        j = i
        while j < length and line[j] in " \t":
            j += 1
        if j < length and line[j] == '"':
            i = j + 1
            buf = []
            while i < length:
                ch = line[i]
                if ch == "\\" and i + 1 < length:
                    buf.append(ch)
                    buf.append(line[i + 1])
                    i += 2
                    continue
                if ch == '"':
                    if i + 1 < length and line[i + 1] == '"':
                        buf.append('"')
                        i += 2
                        continue
                    i += 1
                    while i < length and line[i] in " \t":
                        i += 1
                    break
                buf.append(ch)
                i += 1
            if i < length and line[i] == ",":
                i += 1
            fields.append(("".join(buf), True))
        else:
            buf = []
            while i < length:
                ch = line[i]
                if ch == "\\" and i + 1 < length:
                    buf.append(ch)
                    buf.append(line[i + 1])
                    i += 2
                    continue
                if ch == ",":
                    i += 1
                    break
                buf.append(ch)
                i += 1
            fields.append(("".join(buf), False))
        if i >= length:
            break
    if line.endswith(","):
        fields.append(("", False))
    return fields


def decode_escapes(value):
    out = []
    i = 0
    while i < len(value):
        ch = value[i]
        if ch == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt in ('\\', '"', ","):
                out.append(nxt)
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def parse_date(value):
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    return value


def parse_decimal(value):
    dec = decimal.Decimal(value)
    if dec == dec.to_integral():
        return dec.quantize(decimal.Decimal("1"))
    return dec.normalize()


def normalize_field(header, value, quoted):
    value = decode_escapes(value)
    if not quoted:
        value = value.strip(" \t")
        lowered = value.lower()
        if lowered in NULL_TOKENS:
            return None
        if header in ("ID", "Age") and re.fullmatch(r"[+-]?\d+", value):
            return int(value)
        if header == "Score" and re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
            return parse_decimal(value)
        if header == "Active" and lowered in BOOL_MAP:
            return BOOL_MAP[lowered]
        if header == "Joined":
            parsed = parse_date(value)
            return parsed if isinstance(parsed, dt.date) else value
        return value
    return value


def freeze(value):
    if value is None:
        return ("none", "")
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, decimal.Decimal):
        return ("decimal", render_decimal(value))
    if isinstance(value, dt.date):
        return ("date", value.isoformat())
    return ("str", value)


def render_decimal(value):
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def render_string(value):
    return '"' + value.replace('"', '""') + '"'


def render_value(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, decimal.Decimal):
        return render_decimal(value)
    if isinstance(value, dt.date):
        return value.isoformat()
    return render_string(value)


def transform_text(text):
    lines = [line.rstrip("\n\r") for line in text.splitlines()]
    if not lines:
        raise ValueError("empty input")
    header = [cell for cell, _ in parse_line(lines[0])]
    if header != RAW_HEADERS:
        raise ValueError("unexpected header")
    rows = []
    for line in lines[1:]:
        parsed = parse_line(line)
        if len(parsed) != len(RAW_HEADERS):
            raise ValueError("wrong column count")
        row = {}
        for raw_header, (raw_value, quoted) in zip(RAW_HEADERS, parsed):
            row[RENAME_MAP[raw_header]] = normalize_field(raw_header, raw_value, quoted)
        rows.append(row)
    seen = set()
    unique_rows = []
    for row in rows:
        key = tuple(freeze(row[col]) for col in OUTPUT_HEADERS)
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)
    unique_rows.sort(
        key=lambda row: (
            row["joined_date"] is None,
            row["joined_date"] if isinstance(row["joined_date"], dt.date) else dt.date.max,
            row["id"],
        )
    )
    output_lines = [",".join(OUTPUT_HEADERS)]
    for row in unique_rows:
        output_lines.append(",".join(render_value(row[col]) for col in OUTPUT_HEADERS))
    return "\n".join(output_lines) + "\n"


def main():
    here = pathlib.Path(__file__).resolve().parent
    raw_path = here / "raw_input.csv"
    print(transform_text(raw_path.read_text(encoding="utf-8")), end="")


if __name__ == "__main__":
    main()
