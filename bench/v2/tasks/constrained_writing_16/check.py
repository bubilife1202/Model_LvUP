import json
import re
import sys
from collections import Counter


SENTENCE_RE = re.compile(r"[^.!?]*[.!?]", re.S)


def sentences_of(text):
    return [item.strip() for item in SENTENCE_RE.findall(text) if item.strip()]


def words_of(text):
    return text.split()


def first_word(sentence):
    return words_of(sentence)[0].lstrip("\"'“‘(").rstrip(".,!?;:")


def check(text):
    text = text.strip()
    sentences = sentences_of(text)
    words = words_of(text)
    results = {}

    results["C1"] = len(sentences) == 6
    results["C2"] = len(sentences) == 6 and "".join(
        next(ch for ch in sentence if ch.isalpha()).upper() for sentence in sentences
    ) == "BREEZE"
    counts = [9, 10, 11, 12]
    for idx, target in enumerate(counts, start=1):
        results["C%d" % (idx + 2)] = len(sentences) >= idx and len(words_of(sentences[idx - 1])) == target
    firsts = [first_word(sentence) for sentence in sentences] if sentences else []
    first_counter = Counter(firsts)
    results["C7"] = sum(1 for count in first_counter.values() if count == 2) == 1 and max(first_counter.values() or [0]) == 2
    results["C8"] = first_counter.get("Every", 0) == 2
    results["C9"] = len(re.findall(r"\bcloud\b", text, re.I)) == 3
    results["C10"] = len(re.findall(r"\bgauge\b", text, re.I)) == 3
    cloud = re.search(r"\bcloud\b", text, re.I)
    gauge = re.search(r"\bgauge\b", text, re.I)
    results["C11"] = cloud is not None and gauge is not None and cloud.start() < gauge.start()
    results["C12"] = (
        len(sentences) >= 5
        and bool(re.search(r"\bcloud\b", sentences[4], re.I))
        and bool(re.search(r"\bgauge\b", sentences[4], re.I))
    )
    results["C13"] = sum(sentence.endswith("!") for sentence in sentences) == 1
    results["C14"] = len(sentences) >= 6 and sentences[5].endswith("?")
    results["C15"] = 74 <= len(words) <= 82
    digit_tokens = re.findall(r"\b\d+\b", text)
    results["C16"] = (
        digit_tokens == ["7"]
        and len(sentences) >= 6
        and digit_tokens == re.findall(r"\b\d+\b", sentences[5])
        and not re.search(r"\berror\b", text, re.I)
    )

    passed = sum(1 for value in results.values() if value)
    return {
        "score": passed / 16.0,
        "detail": {
            "passed": passed,
            "total": 16,
            "constraints": results,
        },
    }


if __name__ == "__main__":
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        print(json.dumps(check(handle.read())))
