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
    for row_index, row in enumerate(rows):
        wrapped = [_wrap_cell(cell, widths[col_index]) for col_index, cell in enumerate(row)]
        height = max(len(cell_lines) for cell_lines in wrapped)
        for line_index in range(height):
            parts = []
            for col_index, cell_lines in enumerate(wrapped):
                cell_text = cell_lines[line_index] if line_index < len(cell_lines) else ""
                parts.append(" " + _align(cell_text, widths[col_index], aligns[col_index]) + " ")
            out.append("|" + "|".join(parts) + "|")
        out.append(border)
    return "\n".join(out)
