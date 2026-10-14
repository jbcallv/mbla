import re

from mbla_bench import data

NGRAM = 8
NEAR_DUPLICATE = 0.8
SHINGLE = 3
WORD = re.compile(r"[a-z0-9]+")


def words(text):
    return WORD.findall(text.lower())


def ngrams(text, size):
    tokens = words(text)
    return {tuple(tokens[start : start + size]) for start in range(len(tokens) - size + 1)}


def benchmark_ngrams(item_paths):
    found = set()
    for path in item_paths:
        for item in data.items_by_id(path).values():
            found |= ngrams(item["request"]["text"], NGRAM)
    return found


def leaks(task, forbidden):
    return bool(ngrams(task["text"], NGRAM) & forbidden)


def jaccard(first, second):
    return len(first & second) / len(first | second) if first | second else 1.0


def without_near_duplicates(tasks):
    kept, shingles = [], []
    for task in tasks:
        current = ngrams(task["text"], SHINGLE)
        if all(jaccard(current, earlier) < NEAR_DUPLICATE for earlier in shingles):
            kept.append(task)
            shingles.append(current)
    return kept
