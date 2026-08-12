import re

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
