from datetime import datetime, timedelta


FIELD_RANGES = [
    (0, 59),
    (0, 23),
    (1, 31),
    (1, 12),
    (0, 6),
]


def _parse_iso(value):
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _format_iso(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _expand_piece(piece, minimum, maximum):
    if "/" in piece:
        base, step_text = piece.split("/", 1)
        step = int(step_text)
        if base == "*":
            start, end = minimum, maximum
        else:
            start_text, end_text = base.split("-", 1)
            start, end = int(start_text), int(end_text)
        return set(range(start, end + 1, step))
    if piece == "*":
        return set(range(minimum, maximum + 1))
    if "-" in piece:
        start_text, end_text = piece.split("-", 1)
        start, end = int(start_text), int(end_text)
        return set(range(start, end + 1))
    return {int(piece)}


def _parse_field(text, minimum, maximum):
    allowed = set()
    for piece in text.split(","):
        allowed.update(_expand_piece(piece, minimum, maximum))
    return allowed, text != "*"


def _parse_cron(expr):
    pieces = expr.split()
    parsed = []
    for index, piece in enumerate(pieces):
        allowed, restricted = _parse_field(piece, *FIELD_RANGES[index])
        parsed.append((sorted(allowed), restricted))
    return parsed


def _cron_dow(value):
    return (value.weekday() + 1) % 7


def _date_matches(current, dom_allowed, dom_restricted, dow_allowed, dow_restricted):
    dom_match = current.day in dom_allowed
    dow_match = _cron_dow(current) in dow_allowed
    if dom_restricted and dow_restricted:
        return dom_match or dow_match
    return dom_match and dow_match


def next_fire(cron_expr, after_iso):
    minute_info, hour_info, dom_info, month_info, dow_info = _parse_cron(cron_expr)
    after_dt = _parse_iso(after_iso)
    start = after_dt.replace(second=0, microsecond=0) + timedelta(minutes=1)
    current_date = start.date()

    while True:
        day_start = datetime(current_date.year, current_date.month, current_date.day)
        if day_start.month in month_info[0] and _date_matches(
            day_start, dom_info[0], dom_info[1], dow_info[0], dow_info[1]
        ):
            for hour in hour_info[0]:
                if current_date == start.date() and hour < start.hour:
                    continue
                for minute in minute_info[0]:
                    if current_date == start.date() and hour == start.hour and minute < start.minute:
                        continue
                    candidate = datetime(
                        current_date.year,
                        current_date.month,
                        current_date.day,
                        hour,
                        minute,
                    )
                    if candidate >= start:
                        return _format_iso(candidate)
        current_date += timedelta(days=1)
