"""Constraint checker for T4. Usage: python3 check_t4.py <answer.txt>
Prints JSON: {"passed": k, "total": 12, "failures": [...]}"""
import json
import re
import sys


def sentences_of(text):
    # maximal spans ending in . ! or ?
    spans = re.findall(r"[^.!?]*[.!?]", text, flags=re.S)
    return [s.strip() for s in spans if s.strip()]


def words_of(text):
    return text.split()


def check(text):
    text = text.strip()
    sents = sentences_of(text)
    words = words_of(text)
    results = {}

    results[1] = len(sents) == 8
    results[2] = 120 <= len(words) <= 160
    results[3] = len(words_of(sents[0])) == 9 if sents else False
    results[4] = len(re.findall(r"\blatency\b", text, re.I)) == 3
    results[5] = len(re.findall(r"\bMeridian\b", text)) == 4
    results[6] = all(len(words_of(s)) <= 24 for s in sents) if sents else False
    results[7] = sents[-1].endswith("?") if sents else False
    results[8] = sum(1 for s in sents if s.endswith("!")) == 1
    results[9] = len(re.findall(r"\bdata\b", text, re.I)) == 0
    if len(sents) >= 5:
        first_word = re.sub(r'^["\'“‘(]+', "", words_of(sents[4])[0])
        results[10] = first_word == "Under"
    else:
        results[10] = False
    numbers = re.findall(r"\d[\d,]*(?:\.\d+)?", text)
    results[11] = len(numbers) == 2
    results[12] = all(
        sum(ch.isalpha() for ch in w) <= 14 for w in words
    )

    failures = [f"C{k} failed" for k, v in sorted(results.items()) if not v]
    return {"passed": sum(results.values()), "total": 12, "failures": failures}


if __name__ == "__main__":
    with open(sys.argv[1]) as f:
        print(json.dumps(check(f.read())))
