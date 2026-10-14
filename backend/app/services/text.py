import math
import re
from collections import Counter

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "for", "of", "to", "in", "on", "at", "with",
    "by", "is", "are", "was", "were", "be", "been", "being", "it", "its", "this", "that",
    "these", "those", "from", "as", "into", "over", "under", "about", "than", "then",
    "when", "why", "how", "what", "which", "who", "whom", "whose", "can", "could", "will",
    "would", "should", "shall", "may", "might", "must", "do", "does", "did", "have", "has",
    "had", "not", "no", "yes", "so", "too", "very", "just", "because", "until", "while",
}


def tokenize(content: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", content.lower()) if token not in STOPWORDS]


def content_terms(content: str) -> set[str]:
    return set(tokenize(content))


def bm25_scores(
    query_terms: set[str],
    contents: list[str],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> list[float]:
    """BM25 lexical ranking over the candidate set, normalized to 0..1.

    Proper IDF weighting means rare matching terms dominate common ones,
    fixing the naive set-overlap scorer that ranked any single-term hit
    equally. Returns one score per content string, parallel to the input;
    a query that matches nothing yields all zeros.
    """
    n_docs = len(contents)
    if n_docs == 0 or not query_terms:
        return [0.0] * n_docs

    doc_counts: list[Counter[str]] = [Counter(tokenize(content)) for content in contents]
    doc_lengths = [sum(counts.values()) for counts in doc_counts]
    avg_len = (sum(doc_lengths) / n_docs) or 1.0

    doc_freq: Counter[str] = Counter()
    for counts in doc_counts:
        for term in query_terms:
            if term in counts:
                doc_freq[term] += 1

    scores: list[float] = []
    for counts, length in zip(doc_counts, doc_lengths, strict=True):
        raw = 0.0
        for term in query_terms:
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            df = doc_freq[term]
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            denom = tf + k1 * (1 - b + b * (length / avg_len))
            raw += idf * (tf * (k1 + 1)) / denom
        scores.append(raw)

    top = max(scores, default=0.0)
    if top <= 0:
        return [0.0] * n_docs
    return [score / top for score in scores]
