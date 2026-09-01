"""seeds data models."""

from __future__ import annotations

import hashlib
import os
import re
import time
from collections.abc import Container
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
    """The closed set of relationship types, and it is closed for a reason.

    Every edge is stored at BOTH ends (docs/storage-format.md §5.1), which is
    only unambiguous when the far end can name what it holds: a symmetric type
    stores itself there, a directional type stores a named inverse. So a
    directional type without an inverse cannot be represented on disk at all,
    and adding one later means adding its inverse in the same change. The
    pairing lives in ``seeds.seedfile.inverse_relation``.

    ``QUESTIONED_BY`` is the storage-side inverse of ``QUESTIONS``. It is not
    offered on ``seeds link --type``: a user picks the forward direction and
    the writer lays down the far end.

    ``ANSWERS`` was removed 2026-08-31. It was vestigial — ``seeds answer``
    stores an answer as the question-seed's own content and re-stamps
    ``resolved_at``, and never created an edge — so the corpus held zero of
    them against 534 ``relates-to`` and 57 ``questions``. An edge-based
    answering model was designed and then superseded by the content-field
    approach before anyone used it; only the enum member was left behind.
    """

    RELATES_TO = "relates-to"  # Symmetric: stored as itself at both ends
    QUESTIONS = "questions"  # Directed: question-seed → seed it asks about
    QUESTIONED_BY = "questioned-by"  # The stored inverse of QUESTIONS


def generate_id(prefix: str = "seed") -> str:
    """Generate a short hash-based ID like 'seed-a1b2c3d4'.

    DEPRECATED: ``Store.next_id`` mints ids now. Kept for legacy migration
    code.
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
        dt = dt.replace(tzinfo=UTC)
    return dt


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
    return datetime.now(UTC)


# Sentinel meaning "caller supplied no updated_at". A freshly built seed mirrors
# created_at instead of taking a second clock reading, so that a never-edited
# seed satisfies ``updated_at == created_at`` exactly (two now_utc() calls drift
# by microseconds, which would make has_been_edited() true for every new seed).
UNSET_TIMESTAMP = datetime.min.replace(tzinfo=UTC)


@dataclass
class Seed:
    """A seed as the PRE-0.7 store held it — legacy, conversion-path only.

    The live record is :class:`seeds.seedfile.SeedRecord`, which is what a
    ``.seeds/seeds/<id>.md`` file holds: it carries ``parent``, its own
    relationship list and ``converted_at``, and names the body ``body``. This
    class is the shape of a row in the retired SQLite table and of a line in
    the frozen ``seeds.jsonl``, and it survives for exactly one reason —
    ``seeds convert`` still has to read both of those for the repos that have
    not converted yet (:mod:`seeds.legacy`).

    Nothing on the live path may take a dependency on it.
    """

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

        The live equivalent is :func:`seeds.store.has_been_edited`; this one
        answers the same question about a legacy record.
        """
        return self.updated_at != self.created_at


@dataclass
class Relationship:
    """A typed, directed relationship, as the PRE-0.7 store held it.

    Legacy, like :class:`Seed`: a live edge is a
    :class:`seeds.seedfile.SeedEdge` inside the seed's own file, written at
    both ends (``docs/storage-format.md`` §5.1), with no separate table and so
    no source/target row to name.
    """

    source_id: str
    target_id: str
    rel_type: RelationType = RelationType.RELATES_TO
    created_at: datetime = field(default_factory=now_utc)
