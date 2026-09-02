"""Comparing two pieces of prose for overlap. One implementation, two callers.

``seeds glean`` asks "does the corpus already say this?" and ``seeds winnow``
asks "are these two seeds talking about the same thing?". Both questions reduce
to the same operation — reduce a phrase to its content words and measure how far
one set sits inside the other — and both are load-bearing: glean suppresses a
candidate on the answer, and winnow raises one. Two copies of a tokenizer that
disagreed by a stopword would make the two verbs disagree about the same pair of
sentences, with nothing on screen to say why.

Nothing here concludes anything. Overlap is evidence that two phrases are about
one subject; it is never evidence that they agree or conflict.
"""

from __future__ import annotations

import re

__all__ = ["STOPWORDS", "containment", "content_tokens", "overlap"]

#: Words carried by every sentence, which therefore separate none of them.
#: ``not``, ``no`` and their contractions are here deliberately: polarity is
#: read separately (:mod:`seeds.winnow`), and leaving a negation in the token
#: set would make "we will use X" and "we will not use X" look *less* alike
#: exactly when they most need to be compared.
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "aren't",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "could",
        "did",
        "didn't",
        "do",
        "does",
        "doesn't",
        "don",
        "for",
        "from",
        "get",
        "had",
        "has",
        "have",
        "here",
        "how",
        "i",
        "i'm",
        "if",
        "in",
        "into",
        "is",
        "isn't",
        "it",
        "it's",
        "its",
        "just",
        "like",
        "make",
        "may",
        "me",
        "more",
        "most",
        "much",
        "must",
        "my",
        "no",
        "not",
        "now",
        "of",
        "on",
        "once",
        "one",
        "only",
        "or",
        "other",
        "our",
        "out",
        "over",
        "own",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "that's",
        "the",
        "their",
        "them",
        "then",
        "there",
        "there's",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "use",
        "used",
        "very",
        "was",
        "wasn't",
        "we",
        "we're",
        "were",
        "weren't",
        "what",
        "what's",
        "when",
        "where",
        "which",
        "while",
        "who",
        "why",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)

_WORD_RE = re.compile(r"[a-z0-9][a-z0-9_.-]*")


def content_tokens(text: str) -> set[str]:
    """The content words of a phrase.

    Interior dots, hyphens and underscores are kept — ``seeds-74.2`` and
    ``storage-format.md`` are single words here — but trailing ones are
    stripped. Sentence-final punctuation is otherwise carried into the token,
    and ``transcript.`` then fails to match ``transcript``, which silently costs
    an overlap the comparison was counting on.
    """
    words = (word.strip("._-") for word in _WORD_RE.findall(text.lower()))
    return {word for word in words if len(word) >= 3 and word not in STOPWORDS}


def containment(needle: set[str], haystack: set[str]) -> float:
    """Fraction of ``needle`` present in ``haystack``; 0.0 for an empty needle.

    Directional on purpose. Jaccard would punish a short phrase for being
    quoted inside a long one, which is exactly the case glean has to catch.
    """
    if not needle:
        return 0.0
    return len(needle & haystack) / len(needle)


def overlap(left: set[str], right: set[str]) -> float:
    """Jaccard similarity, for when neither side is the subject of the other."""
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)
