import json
import pathlib
import re


SOURCE_PRIORITY = {"crm": 1, "billing": 2, "support": 3}
SCALAR_FIELDS = ["name", "email", "status", "balance_cents"]
OUTPUT_FIELDS = ["id", "name", "email", "status", "balance_cents", "tags", "updated_at"]


def normalize_id(raw_id):
    value = raw_id.strip().upper()
    value = re.sub(r"[ _]+", "-", value)
    value = re.sub(r"-{2,}", "-", value)
    match = re.fullmatch(r"(.*?)-0*(\d+)", value)
    if match:
        prefix, digits = match.groups()
        return prefix + "-" + str(int(digits))
    return value


def normalize_tags(tags):
    normalized = []
    for tag in tags:
        item = str(tag).strip().lower()
        if item:
            normalized.append(item)
    return normalized


def load_events():
    here = pathlib.Path(__file__).resolve().parent
    all_events = []
    for source_name in ("crm", "billing", "support"):
        path = here / (source_name + ".jsonl")
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            payload = json.loads(line)
            payload["_source"] = source_name
            payload["_priority"] = SOURCE_PRIORITY[source_name]
            payload["_line"] = line_number
            payload["id"] = normalize_id(payload["id"])
            all_events.append(payload)
    return all_events


def order_key(event):
    return (event["updated_at"], event["_priority"], event["_line"])


def merge_records(events):
    grouped = {}
    for event in events:
        grouped.setdefault(event["id"], []).append(event)
    merged = []
    for record_id, items in grouped.items():
        tombstones = [event for event in items if event.get("tombstone")]
        last_tombstone = max(tombstones, key=order_key) if tombstones else None
        if last_tombstone is not None:
            eligible = [event for event in items if order_key(event) > order_key(last_tombstone)]
            if not any(not event.get("tombstone") for event in eligible):
                continue
        else:
            eligible = list(items)
        winners = {}
        updated_at_candidates = []
        for field in SCALAR_FIELDS:
            chosen_event = None
            for event in eligible:
                if event.get("tombstone"):
                    continue
                if field not in event:
                    continue
                if chosen_event is None or order_key(event) > order_key(chosen_event):
                    chosen_event = event
            if chosen_event is not None:
                winners[field] = chosen_event[field]
                updated_at_candidates.append(chosen_event["updated_at"])
        tag_set = set()
        for event in eligible:
            if event.get("tombstone"):
                continue
            tags = event.get("tags")
            if not isinstance(tags, list):
                continue
            for tag in normalize_tags(tags):
                tag_set.add(tag)
            if normalize_tags(tags):
                updated_at_candidates.append(event["updated_at"])
        if "email" in winners and winners["email"] is None:
            del winners["email"]
        if not winners and not tag_set:
            continue
        record = {"id": record_id}
        for field in OUTPUT_FIELDS[1:-1]:
            if field == "tags":
                if tag_set:
                    record["tags"] = sorted(tag_set)
            elif field in winners and winners[field] is not None:
                record[field] = winners[field]
        record["updated_at"] = max(updated_at_candidates)
        merged.append(record)
    merged.sort(key=lambda record: record["id"])
    return merged


def render_lines(records):
    lines = []
    for record in records:
        ordered = {}
        for field in OUTPUT_FIELDS:
            if field in record:
                ordered[field] = record[field]
        lines.append(json.dumps(ordered, ensure_ascii=False, separators=(", ", ": ")))
    return "\n".join(lines) + "\n"


def main():
    print(render_lines(merge_records(load_events())), end="")


if __name__ == "__main__":
    main()
