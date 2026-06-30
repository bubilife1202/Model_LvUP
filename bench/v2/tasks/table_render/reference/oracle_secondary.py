def _explode_word(word, width):
    pieces = []
    index = 0
    while index < len(word):
        pieces.append(word[index:index + width])
        index += width
    return pieces


def _tokenize(text):
    if text == "":
        return []
    tokens = []
    current = []
    for ch in text:
        if ch == " ":
            if current:
                tokens.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        tokens.append("".join(current))
    return tokens


def _wrap_cell(text, width, max_lines=3):
    tokens = _tokenize(text)
    if not tokens:
        lines = [""]
    else:
        lines = []
        current = None
        for token in tokens:
            if len(token) > width:
                if current is not None:
                    lines.append(current)
                    current = None
                lines.extend(_explode_word(token, width))
                continue
            if current is None:
                current = token
                continue
            proposal = current + " " + token
            if len(proposal) <= width:
                current = proposal
            else:
                lines.append(current)
                current = token
        if current is not None:
            lines.append(current)
    if len(lines) > max_lines:
        lines = list(lines[:max_lines])
        if width < 3:
            lines[2] = "." * width
        else:
            lines[2] = lines[2][:width - 3] + "..."
    return lines


def _pad(text, width, align):
    gap = width - len(text)
    if align == "l":
        return text + (" " * gap)
    if align == "r":
        return (" " * gap) + text
    left_gap = gap // 2
    return (" " * left_gap) + text + (" " * (gap - left_gap))


def render_table(rows, widths, aligns):
    segments = ["+"]
    for width in widths:
        segments.append("-" * (width + 2))
        segments.append("+")
    border = "".join(segments)
    if not rows:
        return border + "\n" + border
    rendered = [border]
    for row in rows:
        wrapped_cells = []
        for index, cell in enumerate(row):
            wrapped_cells.append(_wrap_cell(cell, widths[index]))
        row_height = 1
        for lines in wrapped_cells:
            if len(lines) > row_height:
                row_height = len(lines)
        for line_no in range(row_height):
            row_parts = ["|"]
            for index, lines in enumerate(wrapped_cells):
                content = lines[line_no] if line_no < len(lines) else ""
                row_parts.append(" ")
                row_parts.append(_pad(content, widths[index], aligns[index]))
                row_parts.append(" |")
            rendered.append("".join(row_parts))
        rendered.append(border)
    return "\n".join(rendered)
