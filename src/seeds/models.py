"""seeds data models."""

from __future__ import annotations

import hashlib
import os
import re
import time
from collections.abc import Container
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


class SeedStatus(Enum):
    """Lifecycle states for a seed."""

    CAPTURED = "captured"  # Just jotted down, unexplored
    EXPLORING = "exploring"  # Actively being developed
    DEFERRED = "deferred"  # Backlogged for later
    RESOLVED = "resolved"  # Reached a conclusion
    ABANDONED = "abandoned"  # Decided not to pursue


class SeedType(Enum):
    """Categories of seeds."""

    IDEA = "idea"  # General thought
    QUESTION = "question"  # Something needing an answer
    DECISION = "decision"  # A choice made
    EXPLORATION = "exploration"  # Research/investigation notes
    CONCERN = "concern"  # Risk or worry


class RelationType(Enum):
    """Types of relationships between seeds."""

    RELATES_TO = "relates-to"  # Bidirectional, undifferentiated
    QUESTIONS = "questions"  # Directed: question-seed → seed it asks about
    ANSWERS = "answers"  # Directed: answering-seed → question-seed


def generate_id(prefix: str = "seed") -> str:
    """Generate a short hash-based ID like 'seed-a1b2c3d4'.

    DEPRECATED: Use Database.next_id() for sequential IDs instead.
    Kept for legacy migration code.
    """
    data = f"{time.time_ns()}{os.urandom(8).hex()}"
    hash_val = hashlib.sha256(data.encode()).hexdigest()[:8]
    return f"{prefix}-{hash_val}"


# Default project prefix for sequential IDs (used as fallback when no config set)
DEFAULT_PREFIX = "seeds"

# Allowed prefix shape: lowercase letter, then lowercase letters/digits/hyphens.
PREFIX_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def sanitize_prefix(raw: str) -> str:
    """Coerce a string (e.g., a directory name) into a valid ID prefix.

    Rules:
        - Lowercase.
        - Replace runs of non-alphanumeric chars with a single hyphen.
        - Strip leading/trailing hyphens.
        - If the result is empty or starts with a digit, return "" (invalid).

    Examples:
        'My Project'   -> 'my-project'
        'foo_bar.v2'   -> 'foo-bar-v2'
        'seeds'        -> 'seeds'
        '123proj'      -> '' (invalid: starts with digit)
        '!!!'          -> '' (invalid: nothing to anchor on)
    """
    if not raw:
        return ""
    lowered = raw.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not collapsed or not PREFIX_RE.match(collapsed):
        return ""
    return collapsed


def is_valid_prefix(value: str) -> bool:
    """Return True if value is a valid ID prefix (matches PREFIX_RE)."""
    return bool(PREFIX_RE.match(value))


def _id_ref_pattern(old_prefix: str) -> re.Pattern[str]:
    """Compile the regex that matches whole-word seed-ID-shaped tokens.

    The suffix is a base36 token so this spans both ID schemes — base36 hash
    IDs (``seeds-k3n7``) and grandfathered sequential ones (``seeds-112``) —
    with an optional dotted child path. Because a base36 token also matches
    ordinary words, every match must be confirmed by :func:`_is_id_ref`.
    """
    return re.compile(
        rf"(?<![a-zA-Z0-9-]){re.escape(old_prefix)}-([0-9a-z]+(?:\.\d+)*)"
        r"(?![a-zA-Z0-9-])"
    )


def _is_id_ref(suffix: str, old_prefix: str, known_ids: Container[str]) -> bool:
    """Decide whether a matched ``<old_prefix>-<suffix>`` token is a real ID ref.

    A purely numeric suffix is always treated as a reference: that is the
    grandfathered sequential scheme, and matching it unconditionally keeps
    references to since-deleted seeds rewritable.

    A hash-shaped suffix counts only when the ID is in ``known_ids``. No
    heuristic can separate a base36 hash from an English word by shape
    ('seeds-related' is valid base36), so membership in the database is the
    only sound test. ``known_ids`` holds top-level IDs; a child reference is
    judged by its parent.
    """
    top = suffix.split(".", 1)[0]
    if top.isdigit():
        return True
    return f"{old_prefix}-{top}" in known_ids


def rewrite_id_refs(
    text: str,
    old_prefix: str,
    new_prefix: str,
    known_ids: Container[str] = frozenset(),
) -> tuple[str, int]:
    """Rewrite seed-ID references inside a body of text.

    Matches occurrences of ``<old_prefix>-<suffix>`` (with optional
    ``.digits`` children) that are NOT part of a longer identifier — i.e.,
    the character before is not [a-zA-Z0-9-] (or start of string) and the
    character after is not [a-zA-Z0-9-] (or end). This catches references
    like ``see seeds-7`` and ``[seeds-7](url)`` while leaving compound
    tokens like ``seeds-related`` or ``foo-seeds-7-bar`` untouched.

    Numeric suffixes always count as references. Hash-ID references such as
    ``seeds-k3n7`` are rewritten only when listed in ``known_ids`` (the
    top-level IDs present in the database) — see :func:`_is_id_ref`.

    Returns the rewritten text and the number of substitutions made.
    """
    if not text:
        return text, 0
    count = 0

    def replace(m: re.Match[str]) -> str:
        nonlocal count
        if not _is_id_ref(m.group(1), old_prefix, known_ids):
            return m.group(0)
        count += 1
        return f"{new_prefix}-{m.group(1)}"

    return _id_ref_pattern(old_prefix).sub(replace, text), count


_RELATIVE_SINCE_RE = re.compile(r"^(\d+)([dwmy])$")
_RELATIVE_UNIT_DAYS = {"d": 1, "w": 7, "m": 30, "y": 365}


def parse_since(value: str, now: datetime | None = None) -> datetime:
    """Parse a ``--since`` value into a UTC datetime.

    Accepts:
      - ISO 8601 date or datetime: ``'2026-05-08'``,
        ``'2026-05-08T12:00:00+00:00'``
      - Relative: ``'7d'`` (days), ``'2w'`` (weeks), ``'3m'`` (30-day months),
        ``'1y'`` (365-day years)
      - Keywords: ``'today'`` (UTC midnight), ``'yesterday'`` (UTC midnight)

    Naive ISO datetimes are interpreted as UTC. Raises ``ValueError`` on
    unparseable input.
    """
    if not value or not value.strip():
        raise ValueError("--since value cannot be empty")
    if now is None:
        now = now_utc()
    val = value.strip().lower()

    if val == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if val == "yesterday":
        return (now - timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    m = _RELATIVE_SINCE_RE.match(val)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        return now - timedelta(days=n * _RELATIVE_UNIT_DAYS[unit])

    try:
        dt = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Unrecognized --since value {value!r}; expected ISO date "
            f"(2026-05-08), relative (7d, 2w, 3m, 1y), or 'today'/'yesterday'"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


_SUGGEST_TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]*")

# Common English stopwords stripped before building the FTS5 OR query.
# Kept intentionally small — porter stemming handles morphology, this just
# trims dead weight that pollutes BM25.
_SUGGEST_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "he",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "with",
        "we",
        "i",
        "you",
        "they",
        "their",
        "what",
        "which",
        "who",
        "how",
        "when",
        "where",
        "why",
        "all",
        "should",
        "can",
        "could",
        "would",
        "do",
        "does",
        "did",
        "have",
        "had",
        "but",
        "not",
        "some",
        "any",
        "no",
        "yes",
        "if",
        "than",
        "then",
        "so",
        "such",
        "into",
        "out",
        "up",
        "down",
        "over",
        "under",
        "about",
        "between",
        "through",
        "during",
        "after",
        "before",
    }
)


def tokenize_for_suggest(text: str) -> list[str]:
    """Lowercase + strip stopwords for natural-language suggest input.

    Keeps tokens of length 2+ that aren't stopwords. Preserves order and
    keeps duplicates (FTS5 doesn't care, and duplicates are rare in user
    input).
    """
    tokens = _SUGGEST_TOKEN_RE.findall(text.lower())
    return [t for t in tokens if len(t) >= 2 and t not in _SUGGEST_STOPWORDS]


def find_id_refs(
    text: str, prefix: str, known_ids: Container[str] = frozenset()
) -> list[str]:
    """Return sorted, de-duplicated whole-word seed-ID references in ``text``.

    Uses the same matching rules as :func:`rewrite_id_refs`, so it matches
    ``seeds-7`` and ``seeds-12.1`` while leaving compounds like ``seeds-related``
    or ``foo-seeds-7-bar`` alone. Hash-ID references are found only when listed
    in ``known_ids``. Returns ``[]`` for empty input.
    """
    if not text:
        return []
    pattern = _id_ref_pattern(prefix)
    return sorted(
        {
            m.group(0)
            for m in pattern.finditer(text)
            if _is_id_ref(m.group(1), prefix, known_ids)
        }
    )


def iter_id_ref_snippets(
    text: str,
    old_prefix: str,
    new_prefix: str,
    ctx: int = 30,
    known_ids: Container[str] = frozenset(),
) -> list[tuple[str, str]]:
    """List ``(old_snippet, new_snippet)`` pairs for each ID reference change.

    Each snippet includes up to ``ctx`` characters of surrounding context.
    Newlines in the context are collapsed to spaces so previews fit on one
    line. Hash-ID references are included only when listed in ``known_ids``,
    matching :func:`rewrite_id_refs`. Returns an empty list when the text
    contains no matches.
    """
    if not text:
        return []
    pattern = _id_ref_pattern(old_prefix)
    pairs: list[tuple[str, str]] = []
    for m in pattern.finditer(text):
        if not _is_id_ref(m.group(1), old_prefix, known_ids):
            continue
        start, end = m.span()
        ctx_start = max(0, start - ctx)
        ctx_end = min(len(text), end + ctx)
        leading = "…" if ctx_start > 0 else ""
        trailing = "…" if ctx_end < len(text) else ""
        before = text[ctx_start:start].replace("\n", " ")
        after = text[end:ctx_end].replace("\n", " ")
        old_id = m.group(0)
        new_id = f"{new_prefix}-{m.group(1)}"
        pairs.append(
            (
                f"{leading}{before}{old_id}{after}{trailing}",
                f"{leading}{before}{new_id}{after}{trailing}",
            )
        )
    return pairs


def parse_sequential_id(seed_id: str) -> int | None:
    """Extract the sequential number from a seed ID like 'seeds-42'.

    Returns None if the ID is not a sequential format (e.g., hex hash IDs).
    Only parses top-level IDs, not children (seeds-42.1 returns None).
    """
    if "." in seed_id:
        return None
    parts = seed_id.rsplit("-", 1)
    if len(parts) != 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def get_parent_id(seed_id: str) -> str | None:
    """Extract parent ID from a hierarchical seed ID.

    Examples:
        'seed-a1b2' -> None (no parent)
        'seed-a1b2.1' -> 'seed-a1b2'
        'seed-a1b2.1.3' -> 'seed-a1b2.1'
    """
    if "." not in seed_id:
        return None
    return seed_id.rsplit(".", 1)[0]


def now_utc() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class Seed:
    """A seed is an idea at any stage of development."""

    id: str
    title: str
    content: str = ""
    status: SeedStatus = SeedStatus.CAPTURED
    seed_type: SeedType = SeedType.IDEA
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    resolved_at: datetime | None = None
    resolution: str = ""

    @property
    def parent_id(self) -> str | None:
        """Get parent ID from hierarchical ID."""
        return get_parent_id(self.id)

    def is_terminal(self) -> bool:
        """Check if seed is in a terminal state (resolved or abandoned)."""
        return self.status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED)


@dataclass
class ScoredSeed:
    """A seed with a relevance score and matched-text snippet."""

    seed: Seed
    score: float
    snippet: str = ""


@dataclass
class Relationship:
    """A typed, directed relationship between two seeds."""

    source_id: str
    target_id: str
    rel_type: RelationType = RelationType.RELATES_TO
    created_at: datetime = field(default_factory=now_utc)
