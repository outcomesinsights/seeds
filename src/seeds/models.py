"""seeds data models."""

from __future__ import annotations

import hashlib
import os
import re
import time
from collections.abc import Container
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, StrEnum


class SeedStatus(Enum):
    """Lifecycle states for a seed."""

    CAPTURED = "captured"  # Just jotted down, unexplored
    EXPLORING = "exploring"  # Actively being developed
    DEFERRED = "deferred"  # Backlogged for later
    RESOLVED = "resolved"  # Reached a conclusion
    ABANDONED = "abandoned"  # Decided not to pursue


class SeedType(StrEnum):
    """The standard seed vocabulary — a suggestion, not a constraint.

    ``Seed.seed_type`` is a plain ``str`` and any value round-trips through
    storage and sync. This enum names the five types seeds ships with, for
    defaults, for the ``question`` machinery, and for ``seeds doctor`` to tell
    standard types from a project's own.

    Only ``QUESTION`` carries behavior (``seeds ask``/``answer``, ``seeds
    questions``, prime's open-questions section, the web view). The rest are
    display strings. Enforcing them at the storage and sync boundaries broke
    on the first unrecognized value it met — see seed seeds-1x6b.

    A ``StrEnum`` rather than a plain ``Enum`` precisely because the field is
    now a string: ``seed.seed_type == SeedType.QUESTION`` has to keep meaning
    what a reader expects when the left side is ``"question"``. ``SeedStatus``
    stays a closed ``Enum`` — its values do drive behavior.
    """

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


# A bare FTS5 term that needs no quoting: word characters, an optional trailing
# ``*`` for a prefix query. Anything else — a hyphen above all — is punctuation
# FTS5 parses as syntax rather than text.
_FTS_BARE_TERM_RE = re.compile(r"^\w+\*?$", re.UNICODE)

# The operator vocabulary `seeds search --help` documents, plus the two that
# come free with it. FTS5 only treats these as operators in UPPERCASE; a
# lowercase "and" is an ordinary word and gets quoted like any other term.
_FTS_OPERATORS = frozenset({"AND", "OR", "NOT", "NEAR"})

# Splits a query into quoted phrases, parens/commas (NEAR's punctuation), and
# runs of non-space. The phrase alternative comes first so a quoted string is
# taken whole, and its unterminated form is captured rather than dropped.
_FTS_TOKEN_RE = re.compile(r'"[^"]*"\*?|"[^"]*$|[(),]|[^\s(),]+')


def sanitize_fts_query(query: str) -> str:
    """Make a user's search string safe to hand to FTS5 ``MATCH``.

    FTS5 parses punctuation as syntax, so an ordinary hyphenated search term
    is a syntax error rather than a search: ``seeds-to-beads`` reads as a
    column filter and raises ``no such column: to``. Since hyphens are how
    this project names nearly everything — tags, skills, seed IDs — the raw
    string cannot go to MATCH unaltered.

    Terms that need it are wrapped in double quotes, which makes FTS5 read
    them as a phrase. That is not a compromise: the tokenizer splits indexed
    text on the same punctuation, so the phrase ``"seeds-to-beads"`` matches
    exactly the text the user typed it to find.

    The operator syntax `seeds search --help` advertises survives untouched —
    quoted "phrases", ``prefix*``, and uppercase AND/OR/NOT (plus NEAR and its
    parens). Any other FTS5 operator is treated as literal text, which is the
    safe direction to be wrong in: a query that finds nothing beats a
    traceback.

    Returns the empty string when nothing searchable remains (a query of pure
    punctuation), which the caller should read as 'no results' rather than
    passing on to MATCH.
    """
    out: list[str] = []
    for token in _FTS_TOKEN_RE.findall(query):
        if token in {"(", ")", ","} or token in _FTS_OPERATORS:
            out.append(token)
            continue
        if token.startswith('"'):
            # Already a phrase. Close an unterminated one rather than letting
            # FTS5 raise 'unterminated string' on it.
            if not token.rstrip("*").endswith('"') or len(token.rstrip("*")) == 1:
                token = token.rstrip("*") + '"'
            out.append(token)
            continue
        if _FTS_BARE_TERM_RE.match(token):
            out.append(token)
            continue
        prefix = "*" if token.endswith("*") else ""
        body = token[:-1] if prefix else token
        # Nothing but punctuation — FTS5 would reject the empty phrase it
        # produces, and it can match nothing anyway.
        if not any(ch.isalnum() or ch == "_" for ch in body):
            continue
        out.append('"' + body.replace('"', '""') + '"' + prefix)
    return " ".join(out)


# Suffixes that match the ID shape but are prose, never references.
#
# ``<prefix>-<word>`` is ordinary English — "a seeds-native workflow", "the
# seeds-marketplace repo" — and no rule of shape separates it from a base36
# hash ID: ``seeds-like`` is valid base36. Rather than guess, the reference
# validator enumerates the exceptions. A candidate token that names neither a
# seed nor a bead is still accepted when its suffix appears here; everything
# else is reported as a hallucinated ID.
#
# Stored as bare suffixes rather than whole ``seeds-…`` tokens so the
# vocabulary carries over to projects with another prefix (``csc-native``).
#
# To add: when the validator rejects a token you know is prose, put its suffix
# here with a note. Only word-shaped tokens belong — an ID-shaped one quoted as
# an example (``seeds-k3n``) is not prose, and allowlisting it would blind the
# check to that ID forever. Revisit whether this should become per-project
# config only if the list grows past ~20 entries (bead seeds-819).
PROSE_REF_ALLOWLIST = frozenset(
    {
        # Measured across the seeds project's own corpus (seed seeds-6hj5).
        "cli",  # `seeds-cli`, the PyPI name under consideration
        "generated",
        "level",
        "like",
        "marketplace",  # `seeds-marketplace`, the Claude Code plugin marketplace
        "native",
        "side",
        "tool",
        # Found by the pre-ship sweep of the same corpus (bead seeds-819).
        "experiment",  # "`seeds-experiment`-style IDs"
        "recent",  # the `seeds recent` primitive, written `seeds-recent`
        "specific",  # "a seeds-specific phrase"
        "sweep",  # the proposed `/seeds-sweep` slash command
        "whatever",  # placeholder standing in for any ID, in a quoted discussion
    }
)


def is_allowlisted_prose(ref: str, prefix: str) -> bool:
    """Return True when ``ref`` is known prose rather than an ID reference.

    ``ref`` is a whole ``<prefix>-<suffix>`` token as produced by
    :func:`find_id_ref_candidates`; its suffix is matched against
    :data:`PROSE_REF_ALLOWLIST`. A dotted child path never matches — a child
    reference is an ID by construction.
    """
    assert ref.startswith(f"{prefix}-"), ref
    return ref[len(prefix) + 1 :] in PROSE_REF_ALLOWLIST


def find_id_ref_candidates(text: str, prefix: str) -> list[str]:
    """Return sorted, de-duplicated ``<prefix>-…`` tokens that *might* be ID refs.

    Pure extraction: the regex delimits tokens and passes no judgment on them.
    It cannot — ``seeds-like`` is simultaneously an English word and a valid
    base36 hash — so every whole-word match is returned and the caller decides
    whether each names a real seed, a real bead, allowlisted prose
    (:data:`PROSE_REF_ALLOWLIST`), or nothing at all. Tokens buried inside a
    longer identifier (``foo-seeds-7-bar``) are still excluded, since their
    surrounding characters rule them out on shape alone.

    Returns ``[]`` for empty input.
    """
    if not text:
        return []
    return sorted({m.group(0) for m in _id_ref_pattern(prefix).finditer(text)})


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


# Sentinel meaning "caller supplied no updated_at". A freshly built seed mirrors
# created_at instead of taking a second clock reading, so that a never-edited
# seed satisfies ``updated_at == created_at`` exactly (two now_utc() calls drift
# by microseconds, which would make has_been_edited() true for every new seed).
UNSET_TIMESTAMP = datetime.min.replace(tzinfo=timezone.utc)


@dataclass
class Seed:
    """A seed is an idea at any stage of development."""

    id: str
    title: str
    content: str = ""
    status: SeedStatus = SeedStatus.CAPTURED
    seed_type: str = SeedType.IDEA.value
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = UNSET_TIMESTAMP
    resolved_at: datetime | None = None
    resolution: str = ""

    def __post_init__(self) -> None:
        """Default updated_at to created_at rather than a second clock read.

        Also accepts a :class:`SeedType` member for ``seed_type`` and stores
        its value. The field is a plain string so any vocabulary round-trips,
        but ``SeedType.QUESTION`` reads better than ``"question"`` at a call
        site, and callers written before the vocabulary opened still work.
        """
        if self.updated_at == UNSET_TIMESTAMP:
            self.updated_at = self.created_at
        if isinstance(self.seed_type, SeedType):
            self.seed_type = self.seed_type.value

    @property
    def parent_id(self) -> str | None:
        """Get parent ID from hierarchical ID."""
        return get_parent_id(self.id)

    def is_terminal(self) -> bool:
        """Check if seed is in a terminal state (resolved or abandoned)."""
        return self.status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED)

    def has_been_edited(self) -> bool:
        """Whether this seed has been written to since it was created.

        Every interactive write path bumps ``updated_at`` (see
        ``Database.update_seed``), so an untouched seed still carries its
        creation timestamp. Used to tell a seed that has accumulated
        deliberation from one that only ever held its original capture.
        """
        return self.updated_at != self.created_at


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
