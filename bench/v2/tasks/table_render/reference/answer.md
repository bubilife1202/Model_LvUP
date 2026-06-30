```python
def _wrap_cell(text, width, max_lines=3):
    if text == "":
        lines = [""]
    else:
        words = [word for word in text.split(" ") if word]
        lines = []
        current = ""
        for word in words:
            if len(word) > width:
                if current:
                    lines.append(current)
                    current = ""
                start = 0
                while start < len(word):
                    lines.append(word[start:start + width])
                    start += width
                continue
            if not current:
                current = word
            elif len(current) + 1 + len(word) <= width:
                current += " " + word
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        if not lines:
            lines = [""]
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        if width >= 3:
            lines[-1] = lines[-1][:width - 3] + "..."
        else:
            lines[-1] = "." * width
    return lines


def _align(text, width, mode):
    extra = width - len(text)
    if mode == "l":
        return text + (" " * extra)
    if mode == "r":
        return (" " * extra) + text
    left = extra // 2
    right = extra - left
    return (" " * left) + text + (" " * right)


def render_table(rows, widths, aligns):
    border = "+" + "+".join("-" * (width + 2) for width in widths) + "+"
    if not rows:
        return border + "\n" + border
    out = [border]
    for row in rows:
        wrapped = [_wrap_cell(cell, widths[i]) for i, cell in enumerate(row)]
        height = max(len(lines) for lines in wrapped)
        for line_index in range(height):
            parts = []
            for i, lines in enumerate(wrapped):
                text = lines[line_index] if line_index < len(lines) else ""
                parts.append(" " + _align(text, widths[i], aligns[i]) + " ")
            out.append("|" + "|".join(parts) + "|")
        out.append(border)
    return "\n".join(out)
```
