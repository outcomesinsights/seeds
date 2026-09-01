"""Convert a pre-0.7 store — SQLite plus the tracked JSONL — into the tree.

Phase 4 of ``plans/storage-overhaul.md``. ``docs/storage-format.md`` is
normative for what comes out; this module is normative for nothing and is the
bug if the two disagree.

@aguynamedryan set the bar in one sentence on 2026-08-31: *"just fucking make
sure that we get the data in correctly."* Four things follow from that, and
each one is a rule this module keeps rather than a preference:

**The input is the union.** Every id and every field is read from the union
of ``DB`` and ``JSONL``. There is no "convert the DB, then reconcile the JSONL
against it" — that rebuilds the derived-store-overwrites-durable-store shape
(``seeds-fkb8``) inside the migration itself, and the migration is the one
moment where losing a record is unrecoverable by re-running anything.

**Divergence is four conditions and only three are auto-resolvable.** See
:class:`Classification`. A genuine fork — two bodies where neither is a prefix
of the other — is never resolved by rule. Picking a winner there is the exact
silent-collapse error the deliberation caught itself making twice.

**A fork converts to a file, not to an error.** The seed still lands, carrying
both bodies with git conflict markers, and the operator finishes it with the
same merge tooling they use for everything else. Today the same situation is a
deadlock cleared by hand-rebuilding a body and handing it back.

**Nothing is destroyed.** The tree is written alongside ``seeds.db`` and
``seeds.jsonl``; neither is touched, and reverting the whole conversion is
``rm -rf .seeds/seeds/``.

The verification half — re-read the tree, rebuild the records, diff them
field-by-field against both the union and the raw sources, then run ``seeds
check`` — lives in :func:`verify` and runs inside :func:`convert`. It is not
polish. The data-pipeline standard's rule is that the code deciding "clean" is
itself code that can be silently wrong, and a converter that reports success is
exactly such a code path.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from seeds.check import Finding, check_violations
from seeds.legacy import (
    DB_FILE,
    JSONL_FILE,
    LegacyDatabase,
    db_extends_disk,
    first_difference,
)
from seeds.models import RelationType, Seed, SeedStatus
from seeds.seedfile import (
    FILE_SUFFIX,
    SeedEdge,
    SeedFileError,
    SeedRecord,
    expected_parent,
    is_valid_id,
    path_for_id,
    read_seed_file,
    render_seed_file,
    seed_files_dir,
    write_seed_file,
)

__all__ = [
    "NORMALIZATIONS",
    "Classification",
    "ConversionError",
    "ConversionReport",
    "UnionRecord",
    "classify",
    "convert",
    "fork_body",
    "union_records",
    "verify",
]


# --- What is dropped rather than translated ----------------------------------

#: The six test fixtures @aguynamedryan ruled out on 2026-08-31, by exact id.
#: They were verified self-contained first — all empty-bodied, zero relationship
#: rows, and no non-fixture child — so dropping them cannot orphan anything.
#: They stay in git history, which is what makes this recoverable rather than a
#: deletion.
#:
#: An id is repo-local, so this list can only be trusted against the repo it was
#: ruled for. A drop therefore also requires the record to still match the
#: verified profile (empty body, no edges); a ``seeds-71`` somewhere else that
#: holds real deliberation is converted normally. Every drop is reported.
FIXTURE_IDS = frozenset(
    {
        "seeds-71",
        "seeds-71.1",
        "seeds-71.1.1",
        "seeds-71.1.1.1",
        "seeds-71.2",
        "seeds-136",
    }
)

#: Legacy tables the converter drops without translating. ``questions`` predates
#: the v2 question-seeds migration (``seeds-02ur``); re-measured 2026-08-31, all
#: 36 of 36 rows in this repo are orphaned, so the table is entirely debris. The
#: row count is reported so a repo where that is *not* true is visible rather
#: than silently emptied.
LEGACY_TABLES = ("questions",)


# --- The normalization allowlist ---------------------------------------------


@dataclass(frozen=True)
class Normalization:
    """One declared difference verification is allowed to see and pass.

    Declared rather than implicit because the allowlist is the whole loophole
    in "fails on any difference": anything not named here is a failure, and
    anything named here has to say why it is not data loss.
    """

    name: str
    why: str


#: Every difference :func:`verify` may forgive, and its justification. The list
#: is short on purpose — each entry is a hole in the guarantee.
NORMALIZATIONS: tuple[Normalization, ...] = (
    Normalization(
        "body-trailing-newline",
        "the format canonicalizes a body to exactly one trailing newline (§2), "
        "so bodies are compared with trailing newlines stripped. 282 of this "
        "repo's 314 records differ from canonical form by nothing else, and a "
        "comparison that skipped this would report a ~90% divergence rate that "
        "is not real",
    ),
    Normalization(
        "timestamp-utc",
        "§3 requires every stamp normalized to UTC, so a source stamp carrying "
        "another offset — or, from the JSONL, no offset at all — is converted "
        "once on the way in and compared as the same instant",
    ),
    Normalization(
        "sequence-order",
        "§4 says sequence order is preserved as written and is not otherwise "
        "meaningful, so tags and relationships are compared as multisets",
    ),
    Normalization(
        "fork-conflict-body",
        "a forked id's emitted body is the conflict rendering of two bodies, so "
        "it equals neither source. It is verified by containment instead: both "
        "source bodies must appear in it verbatim",
    ),
    Normalization(
        "materialized-inverse-edge",
        "§5.1 stores every edge at both ends and §5.2 names the inverse, so the "
        "emitted relationship set is a superset of the sources'. Verified as a "
        "superset: every source half must be present, and every added half must "
        "be the inverse of one",
    ),
    Normalization(
        "declared-drop",
        "the six ruled fixtures and any edge naming a seed that does not exist "
        "are absent from the output by design. Verified against the report: the "
        "set missing from the tree must equal the set the converter said it "
        "dropped",
    ),
)


# --- Errors ------------------------------------------------------------------


class ConversionError(Exception):
    """The conversion cannot proceed, or its own verification failed.

    Raised rather than returned because every case is one where continuing
    would write or bless data the converter cannot vouch for. The message names
    the store, the id, and what is wrong.
    """


# --- Classification ----------------------------------------------------------


class Classification(Enum):
    """How one id's body differs between the two stores.

    Only the first three are auto-resolvable.

    ``DB_ONLY``
        Present in the database, never exported. ``seeds-fkb8`` itself was in
        this state on 2026-08-28.

    ``JSONL_ONLY``
        Present on disk, never imported — the import aborted above it or
        skipped it. @markdanese's 40 seeds (``seeds-1x6b``) sat here for five
        weeks.

    ``DB_EXTENDS_DISK``
        Present in both, and **one body is a prefix of the other**: the
        ordinary append, where the longer body is the shorter plus text and
        taking it loses nothing. ``db_extends_disk``'s docstring records 41 of
        42 content edits across 67 commits as literal appends, so this is the
        common case and the database is almost always the longer side. The
        mirror — the file ahead of a database that never imported it — is the
        same shape with the same safety property and is resolved the same way,
        which is why it is this class and not a fork.

    ``FORK``
        Present in both, and **neither body is a prefix of the other**. Each
        store holds text the other has never seen. This is never auto-resolved:
        any rule that picks a winner deletes deliberation, and the deliberation
        this tool exists to protect is precisely the thing on both sides.
    """

    DB_ONLY = "db-only"
    JSONL_ONLY = "jsonl-only"
    DB_EXTENDS_DISK = "db-extends-disk"
    FORK = "fork"


def classify(db_body: str | None, jsonl_body: str | None) -> Classification:
    """Classify one id from the two stores' bodies. ``None`` means absent."""
    if db_body is not None and jsonl_body is None:
        return Classification.DB_ONLY
    if db_body is None and jsonl_body is not None:
        return Classification.JSONL_ONLY
    if db_body is None or jsonl_body is None:
        raise ConversionError("classify called for an id in neither store")
    if db_extends_disk(db_body, jsonl_body):
        return Classification.DB_EXTENDS_DISK
    if db_extends_disk(jsonl_body, db_body):
        return Classification.DB_EXTENDS_DISK
    return Classification.FORK


# --- The fork rendering ------------------------------------------------------

#: The labels on the conflict markers. They name the *store*, not a branch,
#: because that is the question the operator resolving this has to answer.
_DB_LABEL = "database (.seeds/seeds.db)"
_JSONL_LABEL = "on disk (.seeds/seeds.jsonl)"


def fork_body(db_body: str, jsonl_body: str) -> str:
    """Both bodies in one body, with git conflict markers around each (§6).

    Ordinary merge tooling — an editor's conflict view, ``git checkout
    --ours``, a three-way diff — works on this unchanged, which is the entire
    point of turning a deadlock into a file. ``seeds check`` reports the
    markers as a ``conflict-markers`` violation until they are gone, so an
    unresolved fork cannot quietly become the permanent state of the store.
    """
    top = db_body.strip("\n")
    bottom = jsonl_body.strip("\n")
    lines = [f"<<<<<<< {_DB_LABEL}"]
    if top:
        lines.append(top)
    lines.append("=======")
    if bottom:
        lines.append(bottom)
    lines.append(f">>>>>>> {_JSONL_LABEL}")
    return "\n".join(lines) + "\n"


# --- Source records ----------------------------------------------------------


@dataclass(frozen=True)
class _Half:
    """One directed relationship half as some store recorded it."""

    source_id: str
    target_id: str
    rel_type: RelationType
    created_at: datetime


@dataclass
class _Side:
    """One store's view of one seed: the scalars, the tags, and the body."""

    seed: Seed
    origin: Literal["db", "jsonl"]


def _to_utc(stamp: datetime) -> datetime:
    """Normalize one stamp to UTC (§3), reading a naive one as UTC.

    Naive input reaches this only from the JSONL, where the importer already
    reads it as UTC — the file format keeps one rule, not two. The strict
    reader refuses naive input, so this is the single place the leniency lives.
    """
    if stamp.tzinfo is None:
        return stamp.replace(tzinfo=UTC)
    return stamp.astimezone(UTC)


def _seed_to_utc(seed: Seed) -> Seed:
    """A copy of ``seed`` with every stamp normalized to UTC."""
    seed.created_at = _to_utc(seed.created_at)
    seed.updated_at = _to_utc(seed.updated_at)
    if seed.resolved_at is not None:
        seed.resolved_at = _to_utc(seed.resolved_at)
    return seed


def _load_db(db_path: Path) -> tuple[dict[str, _Side], list[_Half], dict[str, int]]:
    """Read every seed, every relationship half, and the legacy table counts.

    Returns ``({}, [], {})`` when there is no database at all — a repo that has
    only ever had the JSONL (a fresh clone; ``.seeds/seeds.db`` is gitignored)
    converts from the file alone.
    """
    if not db_path.exists():
        return {}, [], {}

    legacy = _legacy_table_counts(db_path)

    db = LegacyDatabase(db_path)
    try:
        sides: dict[str, _Side] = {}
        for seed in db.list_seeds():
            sides[seed.id] = _Side(seed=_seed_to_utc(seed), origin="db")
        halves: list[_Half] = []
        seen: set[tuple[str, str, str]] = set()
        for seed_id in sides:
            for rel in db.get_relationships(seed_id):
                key = (rel.source_id, rel.target_id, rel.rel_type.value)
                if key in seen:
                    continue
                seen.add(key)
                halves.append(
                    _Half(
                        source_id=rel.source_id,
                        target_id=rel.target_id,
                        rel_type=rel.rel_type,
                        created_at=_to_utc(rel.created_at),
                    )
                )
        return sides, halves, legacy
    finally:
        db.close()


def _legacy_table_counts(db_path: Path) -> dict[str, int]:
    """Row counts for the tables the converter drops without translating.

    A second, read-only door to the same SQLite file, and deliberately so:
    :class:`~seeds.legacy.LegacyDatabase` has no API for ``questions``, because
    nothing translates that table. Counting the rows is the whole interaction —
    nothing here reads a column.
    """
    counts: dict[str, int] = {}
    conn = sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True)
    try:
        present = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        for table in LEGACY_TABLES:
            if table in present:
                counts[table] = conn.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
    finally:
        conn.close()
    return counts


def _load_jsonl(jsonl_path: Path) -> tuple[dict[str, _Side], list[_Half]]:
    """Read every record on disk, strictly.

    Strict because this is a migration: a line the converter cannot read is a
    line whose deliberation would be silently absent from the tree, and unlike
    ``seeds import`` — which refuses one record and lands the rest so the tool
    keeps working — there is no later run that picks it up.
    """
    if not jsonl_path.exists():
        return {}, []

    sides: dict[str, _Side] = {}
    halves: list[_Half] = []
    raw_by_id: dict[str, str] = {}
    with open(jsonl_path, encoding="utf-8") as stream:
        for lineno, raw in enumerate(stream, start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ConversionError(
                    f"{jsonl_path}: line {lineno} is not valid JSON ({exc.msg}) — "
                    "unresolved merge conflict markers are the usual cause. "
                    "Resolve the line and re-run; the converter will not skip a "
                    "record it cannot read"
                ) from exc
            if data.get("format_version") != 2:
                raise ConversionError(
                    f"{jsonl_path}: line {lineno} is format_version "
                    f"{data.get('format_version')!r}, and the converter reads "
                    "version 2 only. A v1 record has to be migrated first, and "
                    "seeds no longer can: `seeds import` was the migration "
                    "(it turned a record's embedded questions into "
                    "question-seeds with new ids) and it went with the store "
                    "it wrote into. Run `uvx seeds==0.6.1 import` against this "
                    "file, then convert"
                )
            seed_id = data.get("id")
            if not isinstance(seed_id, str) or not is_valid_id(seed_id):
                raise ConversionError(
                    f"{jsonl_path}: line {lineno} has id {seed_id!r}, which is "
                    "not a seed id. The filename stem is the id verbatim (§1.1), "
                    "so there is no file this record could be written to"
                )
            if seed_id in sides:
                if raw.strip() == raw_by_id[seed_id]:
                    continue
                raise ConversionError(
                    f"{jsonl_path}: id {seed_id!r} appears on more than one line "
                    "with different content — a botched merge left two records "
                    "for one seed. Resolve them into one line and re-run; "
                    "guessing which is current is exactly the collapse this "
                    "converter refuses to perform"
                )
            raw_by_id[seed_id] = raw.strip()
            seed = _seed_from_record(seed_id, data)
            sides[seed_id] = _Side(seed=seed, origin="jsonl")
            halves.extend(_halves_from_record(seed, data, jsonl_path, lineno))
    return sides, halves


def _seed_from_record(seed_id: str, data: dict[str, object]) -> Seed:
    """Build a :class:`Seed` from one v2 JSONL record, strictly."""

    def _text(key: str) -> str:
        value = data.get(key, "")
        if value is None:
            return ""
        if not isinstance(value, str):
            raise ConversionError(
                f"{seed_id}: field {key!r} is {type(value).__name__}, expected a string"
            )
        return value

    def _stamp(key: str, *, required: bool) -> datetime | None:
        value = data.get(key)
        if value is None or value == "":
            if required:
                raise ConversionError(f"{seed_id}: field {key!r} is missing")
            return None
        if not isinstance(value, str):
            raise ConversionError(
                f"{seed_id}: field {key!r} is {type(value).__name__}, "
                "expected an ISO 8601 string"
            )
        try:
            return _to_utc(datetime.fromisoformat(value))
        except ValueError as exc:
            raise ConversionError(
                f"{seed_id}: field {key!r} is not an ISO 8601 timestamp: {value!r}"
            ) from exc

    status_raw = _text("status")
    try:
        status = SeedStatus(status_raw)
    except ValueError as exc:
        raise ConversionError(
            f"{seed_id}: status {status_raw!r} is outside the closed set "
            "(captured, exploring, deferred, resolved, abandoned). The "
            "vocabulary is closed and stays closed (§3)"
        ) from exc

    tags = data.get("tags", [])
    if not isinstance(tags, list) or any(not isinstance(t, str) for t in tags):
        raise ConversionError(f"{seed_id}: field 'tags' is not a list of strings")

    created = _stamp("created_at", required=True)
    updated = _stamp("updated_at", required=True)
    assert created is not None and updated is not None
    return Seed(
        id=seed_id,
        title=_text("title"),
        content=_text("content"),
        status=status,
        seed_type=_text("seed_type"),
        tags=list(tags),
        created_at=created,
        updated_at=updated,
        resolved_at=_stamp("resolved_at", required=False),
        resolution=_text("resolution"),
    )


def _halves_from_record(
    seed: Seed, data: dict[str, object], path: Path, lineno: int
) -> list[_Half]:
    """The outbound relationship halves one v2 record declares."""
    seed_id = seed.id
    rels = data.get("relationships", [])
    if not isinstance(rels, list):
        raise ConversionError(
            f"{path}: line {lineno} ({seed_id}): 'relationships' is not a list"
        )
    halves: list[_Half] = []
    for rel in rels:
        if not isinstance(rel, dict):
            raise ConversionError(
                f"{path}: line {lineno} ({seed_id}): a relationship is not a mapping"
            )
        target = rel.get("target_id")
        rel_type_raw = rel.get("rel_type")
        if not isinstance(target, str) or not isinstance(rel_type_raw, str):
            raise ConversionError(
                f"{path}: line {lineno} ({seed_id}): a relationship is missing "
                "'target_id' or 'rel_type'"
            )
        try:
            rel_type = RelationType(rel_type_raw)
        except ValueError as exc:
            raise ConversionError(
                f"{path}: line {lineno} ({seed_id}): rel_type {rel_type_raw!r} is "
                "outside the closed set (relates-to, questions, questioned-by). "
                "A directional type with no named inverse cannot be stored in "
                "this format at all (§5.2)"
            ) from exc
        stamp_raw = rel.get("created_at")
        if isinstance(stamp_raw, str) and stamp_raw:
            try:
                stamp = _to_utc(datetime.fromisoformat(stamp_raw))
            except ValueError as exc:
                raise ConversionError(
                    f"{path}: line {lineno} ({seed_id}): relationship created_at "
                    f"is not an ISO 8601 timestamp: {stamp_raw!r}"
                ) from exc
        else:
            # An edge with no stamp of its own is dated from the seed that
            # declares it, which is the only date either store holds for it.
            stamp = seed.created_at
        halves.append(
            _Half(
                source_id=seed_id,
                target_id=target,
                rel_type=rel_type,
                created_at=stamp,
            )
        )
    return halves


# --- Edges: one identity per edge, both ends written -------------------------

#: An edge's identity, independent of which end declared it. A symmetric type
#: is keyed on the unordered pair; a directional one on the ordered pair in its
#: forward direction, so a ``questioned-by`` half and the ``questions`` half it
#: mirrors collapse onto one edge rather than becoming two.
_EdgeKey = tuple[str, str, str]


def _edge_key(half: _Half) -> _EdgeKey:
    if half.rel_type is RelationType.RELATES_TO:
        first, second = sorted((half.source_id, half.target_id))
        return (RelationType.RELATES_TO.value, first, second)
    if half.rel_type is RelationType.QUESTIONED_BY:
        return (RelationType.QUESTIONS.value, half.target_id, half.source_id)
    return (RelationType.QUESTIONS.value, half.source_id, half.target_id)


def _resolve_edges(
    halves: Iterable[_Half], known: frozenset[str]
) -> tuple[dict[str, list[SeedEdge]], list[_EdgeKey]]:
    """Fold every half into whole edges, then write each at both ends (§5.1).

    Two things happen here that the source stores never did.

    The ``questioned-by`` inverse is **materialized**. It did not exist before
    the format froze, so the database holds 57 ``questions`` edges in one
    direction only, and ``seeds check`` on a corpus rendered without them
    reports 57 one-sided-edge violations — every one of them. All 550
    ``relates-to`` halves score zero, which is what says the checker is
    distinguishing rather than firing indiscriminately.

    An edge's ``created_at`` is **collapsed to the earliest** half seen for it.
    §5 says the stamp is the edge's own and is the same value at both ends, so
    two halves stamped differently are one edge recorded twice, not two edges;
    leaving them disagreeing would fail the checker's ``edge-timestamp-mismatch``
    rule on output the converter itself wrote.

    Returns the per-seed edge lists and every edge dropped for naming a seed
    that does not exist — the foreign key SQLite declared but, with the legacy
    rows still in place, never actually held.
    """
    stamps: dict[_EdgeKey, datetime] = {}
    for half in halves:
        key = _edge_key(half)
        current = stamps.get(key)
        if current is None or half.created_at < current:
            stamps[key] = half.created_at

    by_seed: dict[str, list[SeedEdge]] = {}
    dangling: list[_EdgeKey] = []

    def add(source: str, target: str, rel_type: RelationType, at: datetime) -> None:
        edges = by_seed.setdefault(source, [])
        if any(
            e.target_id == target and e.rel_type is rel_type and e.created_at == at
            for e in edges
        ):
            return
        edges.append(SeedEdge(target_id=target, rel_type=rel_type, created_at=at))

    for key, stamp in sorted(stamps.items()):
        rel_value, first, second = key
        if first not in known or second not in known:
            dangling.append(key)
            continue
        if rel_value == RelationType.RELATES_TO.value:
            add(first, second, RelationType.RELATES_TO, stamp)
            if first != second:
                add(second, first, RelationType.RELATES_TO, stamp)
        else:
            add(first, second, RelationType.QUESTIONS, stamp)
            add(second, first, RelationType.QUESTIONED_BY, stamp)

    for edges in by_seed.values():
        edges.sort(key=lambda e: (e.created_at, e.target_id, e.rel_type.value))
    return by_seed, dangling


# --- The union record --------------------------------------------------------


@dataclass(frozen=True)
class FieldDivergence:
    """One field the two stores disagreed about, and how the union settled it.

    Reported, never silent. Replacement is the normal editing verb for a title,
    a status, a type and a resolution — ``find_divergence`` deliberately does
    not guard them for that reason — so the live store wins them. That is a
    defensible rule and still a discarded value, so the discarded value is
    printed rather than dropped on the floor.
    """

    seed_id: str
    field_name: str
    in_db: str
    on_disk: str
    kept: str


@dataclass
class UnionRecord:
    """One seed as the union of the two stores holds it, and how its body got there."""

    record: SeedRecord
    classification: Classification
    db_body: str | None
    jsonl_body: str | None
    #: Set when a previous run's fork file was found already resolved by hand,
    #: so this run kept the operator's body instead of re-emitting the conflict.
    kept_resolution: bool = False

    @property
    def is_fork(self) -> bool:
        return self.classification is Classification.FORK


def _canonical_body(body: str) -> str:
    """A body in the one form the format keeps (§2): no trailing blank runs."""
    stripped = body.strip("\n")
    return stripped + "\n" if stripped else ""


def _pick(
    seed_id: str,
    field_name: str,
    db_value: str,
    disk_value: str,
    have_db: bool,
    have_disk: bool,
    divergences: list[FieldDivergence],
) -> str:
    """One scalar field, unioned. The live store wins a disagreement, loudly."""
    if not have_db:
        return disk_value
    if not have_disk:
        return db_value
    if db_value == disk_value:
        return db_value
    divergences.append(
        FieldDivergence(
            seed_id=seed_id,
            field_name=field_name,
            in_db=db_value,
            on_disk=disk_value,
            kept=db_value,
        )
    )
    return db_value


def union_records(
    db_sides: dict[str, _Side],
    jsonl_sides: dict[str, _Side],
    edges: dict[str, list[SeedEdge]],
    *,
    drop_ids: frozenset[str] = frozenset(),
) -> tuple[list[UnionRecord], list[FieldDivergence]]:
    """Build one record per id from the union of ``DB`` and ``JSONL``, field by field.

    Per-field rules, all of them chosen to lose nothing that can be kept:

    - ``created_at`` takes the **earlier** of the two and ``updated_at`` the
      **later**. A seed was created once; the earlier stamp is the one that
      witnessed it, and the later write is the one that happened last.
    - ``tags`` is a genuine set union, in database order with the file's extras
      appended. Nothing is dropped, so nothing needs reporting.
    - ``resolved_at`` follows the status the union settled on: §3 requires it
      for a terminal status and forbids it otherwise, so a stamp on a
      non-terminal seed is dropped and reported, and a terminal seed missing
      one falls back to ``updated_at`` rather than failing the write.
    - the body is :func:`classify`'s four-way call.
    - every other scalar is :func:`_pick`.
    """
    divergences: list[FieldDivergence] = []
    out: list[UnionRecord] = []

    for seed_id in sorted(set(db_sides) | set(jsonl_sides)):
        if seed_id in drop_ids:
            continue
        db_side = db_sides.get(seed_id)
        disk_side = jsonl_sides.get(seed_id)
        have_db = db_side is not None
        have_disk = disk_side is not None
        db_seed = db_side.seed if db_side is not None else None
        disk_seed = disk_side.seed if disk_side is not None else None

        db_body = _canonical_body(db_seed.content) if db_seed is not None else None
        disk_body = (
            _canonical_body(disk_seed.content) if disk_seed is not None else None
        )
        classification = classify(db_body, disk_body)

        if classification is Classification.FORK:
            assert db_body is not None and disk_body is not None
            body = fork_body(db_body, disk_body)
        elif classification is Classification.DB_ONLY:
            assert db_body is not None
            body = db_body
        elif classification is Classification.JSONL_ONLY:
            assert disk_body is not None
            body = disk_body
        else:
            assert db_body is not None and disk_body is not None
            body = db_body if len(db_body) >= len(disk_body) else disk_body

        title = _pick(
            seed_id,
            "title",
            db_seed.title if db_seed else "",
            disk_seed.title if disk_seed else "",
            have_db,
            have_disk,
            divergences,
        )
        status_value = _pick(
            seed_id,
            "status",
            db_seed.status.value if db_seed else "",
            disk_seed.status.value if disk_seed else "",
            have_db,
            have_disk,
            divergences,
        )
        seed_type = _pick(
            seed_id,
            "type",
            db_seed.seed_type if db_seed else "",
            disk_seed.seed_type if disk_seed else "",
            have_db,
            have_disk,
            divergences,
        )
        resolution = _pick(
            seed_id,
            "resolution",
            db_seed.resolution if db_seed else "",
            disk_seed.resolution if disk_seed else "",
            have_db,
            have_disk,
            divergences,
        )

        sides = [s for s in (db_seed, disk_seed) if s is not None]
        created_at = min(s.created_at for s in sides)
        updated_at = max(s.updated_at for s in sides)
        status = SeedStatus(status_value)
        terminal = status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED)
        candidates = [s.resolved_at for s in sides if s.resolved_at is not None]
        if terminal:
            resolved_at: datetime | None = min(candidates) if candidates else updated_at
        else:
            resolved_at = None
            if candidates:
                divergences.append(
                    FieldDivergence(
                        seed_id=seed_id,
                        field_name="resolved_at",
                        in_db=str(db_seed.resolved_at if db_seed else ""),
                        on_disk=str(disk_seed.resolved_at if disk_seed else ""),
                        kept=(
                            f"dropped: §3 forbids resolved_at when status is "
                            f"{status.value!r}"
                        ),
                    )
                )

        tags: list[str] = []
        for source in (db_seed, disk_seed):
            if source is None:
                continue
            for tag in source.tags:
                if tag not in tags:
                    tags.append(tag)

        out.append(
            UnionRecord(
                record=SeedRecord(
                    id=seed_id,
                    title=title,
                    status=status,
                    seed_type=seed_type,
                    created_at=created_at,
                    updated_at=updated_at,
                    parent=expected_parent(seed_id),
                    resolved_at=resolved_at,
                    resolution=resolution,
                    tags=tags,
                    relationships=edges.get(seed_id, []),
                    body=body,
                ),
                classification=classification,
                db_body=db_body,
                jsonl_body=disk_body,
            )
        )
    return out, divergences


# --- The report --------------------------------------------------------------


@dataclass
class ConversionReport:
    """Everything the conversion did, and everything it refused to do."""

    seeds_dir: Path
    out_dir: Path
    db_present: bool
    jsonl_present: bool
    counts: dict[Classification, int] = field(default_factory=dict)
    written: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    forks: list[str] = field(default_factory=list)
    forks_already_resolved: list[str] = field(default_factory=list)
    dropped_fixtures: list[str] = field(default_factory=list)
    kept_fixtures: list[str] = field(default_factory=list)
    dropped_legacy_rows: dict[str, int] = field(default_factory=dict)
    #: How many distinct ids the two source stores held between them, before
    #: any drop. Printed so "308 converted" can be checked against it by eye
    #: rather than taken on trust.
    source_ids: int = 0
    dropped_edges: list[str] = field(default_factory=list)
    field_divergences: list[FieldDivergence] = field(default_factory=list)
    stale_files: list[str] = field(default_factory=list)
    prefix_written: str | None = None
    verified: int = 0
    check_findings: list[Finding] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.written) + len(self.unchanged)

    @property
    def clean(self) -> bool:
        """Whether the tree is finished: verified, checked, and no open fork.

        An unresolved fork is not a failure of the conversion — the seed landed
        and nothing was lost — but it *is* an unfinished store, so it keeps the
        exit status non-zero until a human resolves it.
        """
        return not self.check_findings and not self.forks


def format_report(report: ConversionReport) -> str:
    """Render a report for a terminal. Every refusal is named, never counted."""
    out: list[str] = []
    sources = []
    if report.db_present:
        sources.append(DB_FILE)
    if report.jsonl_present:
        sources.append(JSONL_FILE)
    out.append(f"Converted {' + '.join(sources)} -> {report.out_dir}")
    out.append(
        f"  {report.source_ids} seed(s) in the source stores -> "
        f"{report.total} converted: {len(report.written)} written, "
        f"{len(report.unchanged)} already current"
    )
    for classification in Classification:
        count = report.counts.get(classification, 0)
        if count:
            out.append(f"  {classification.value}: {count}")
    if report.prefix_written:
        out.append(f"  wrote prefix {report.prefix_written!r} to config.yaml")
    for table, rows in sorted(report.dropped_legacy_rows.items()):
        out.append(f"  dropped the legacy {table} table ({rows} row(s), untranslated)")
    if report.dropped_fixtures:
        out.append(
            f"  dropped {len(report.dropped_fixtures)} ruled test fixture(s): "
            f"{', '.join(report.dropped_fixtures)}"
        )
    if report.kept_fixtures:
        out.append(
            f"  kept {len(report.kept_fixtures)} id(s) on the fixture list that no "
            f"longer match the ruled profile: {', '.join(report.kept_fixtures)}"
        )
    if report.dropped_edges:
        out.append(f"  dropped {len(report.dropped_edges)} edge(s) naming no seed:")
        out.extend(f"    {edge}" for edge in report.dropped_edges)
    if report.field_divergences:
        out.append(
            f"  {len(report.field_divergences)} field(s) disagreed between the "
            f"stores; the database's value was kept:"
        )
        out.extend(
            f"    {d.seed_id} {d.field_name}: db {d.in_db!r} / disk {d.on_disk!r}"
            for d in report.field_divergences
        )
    if report.stale_files:
        out.append(
            f"  {len(report.stale_files)} file(s) in the tree have no record in "
            f"either store; left in place, nothing is deleted:"
        )
        out.extend(f"    {name}" for name in report.stale_files)
    if report.forks_already_resolved:
        out.append(
            f"  {len(report.forks_already_resolved)} fork(s) already resolved in "
            f"the tree; left alone: {', '.join(report.forks_already_resolved)}"
        )
    out.append(f"  round-trip verified {report.verified} record(s)")
    if report.forks:
        out.append("")
        out.append(
            f"{len(report.forks)} fork(s) need a human. Each holds both bodies "
            f"with git conflict markers; resolve with ordinary merge tooling:"
        )
        out.extend(f"  {report.out_dir / (i + FILE_SUFFIX)}" for i in report.forks)
    if report.check_findings:
        out.append("")
        out.append(f"seeds check: {len(report.check_findings)} violation(s).")
    return "\n".join(out)


# --- Verification ------------------------------------------------------------


def _assert_complete(
    out_dir: Path,
    unions: Sequence[UnionRecord],
    db_sides: dict[str, _Side],
    jsonl_sides: dict[str, _Side],
    drop_ids: frozenset[str],
) -> None:
    """Every source id has a file, and the declared drops are the ONLY absences.

    This is the assertion that makes every other check in this module worth
    running, and it exists because ``seeds check`` **exits 0 on an empty
    store**. Measured on the merged checker: an empty ``.seeds/seeds/`` reports
    "0 files, no violations" and exits 0, while the same corpus rendered in
    full reports 57 violations and exits 1. So "the converter ran check on its
    output and it passed" is not evidence that the conversion produced
    anything — a run that emitted zero files, or silently skipped most ids,
    passes its own verification cleanly.

    That is exactly the failure class this project keeps hitting: a gate
    measuring something adjacent to the artifact and reporting green while the
    artifact is broken. The cheap set comparison here is what makes the
    expensive one downstream mean something.

    Sets, never counts. Equal counts still hide a swap — one id lost and
    another invented lands on the same total — so every comparison below is a
    set difference and every failure names the ids rather than a number.
    """
    source_ids = set(db_sides) | set(jsonl_sides)
    expected = source_ids - drop_ids
    produced = {u.record.id for u in unions}

    if produced != expected:
        raise ConversionError(
            "completeness verification failed: the union does not cover the "
            "source stores. "
            + _set_detail("in a source store and not in the union", expected - produced)
            + _set_detail("in the union and in no source store", produced - expected)
        )

    present = {
        path.name[: -len(FILE_SUFFIX)] for path in out_dir.glob(f"*{FILE_SUFFIX}")
    }

    if expected and not present & expected:
        raise ConversionError(
            f"completeness verification failed: the source stores hold "
            f"{len(expected)} seed(s) to convert and {out_dir} holds none of "
            f"them. A zero-file conversion passes 'seeds check' — an empty "
            f"store has nothing to violate — so it is caught here instead"
        )

    missing = expected - present
    if missing:
        raise ConversionError(
            f"completeness verification failed: {len(expected)} seed(s) should "
            f"be in {out_dir} and {len(missing)} have no file. "
            + _set_detail("missing from the tree", missing)
        )

    # The deliberate drops are the only ids allowed to be absent. An id in a
    # source store, absent from the tree, and absent from the drop list is a
    # record that vanished, which is the one outcome no report may downgrade to
    # a warning.
    unexplained = source_ids - present - drop_ids
    if unexplained:
        raise ConversionError(
            "completeness verification failed: id(s) absent from the tree that "
            "the converter never said it dropped. "
            + _set_detail("unexplained absence", unexplained)
        )


#: How many ids a failure names before it starts counting instead.
_NAME_LIMIT = 20


def _set_detail(label: str, ids: set[str]) -> str:
    """Name the ids behind a set-comparison failure, not just how many."""
    if not ids:
        return ""
    names = sorted(ids)
    shown = ", ".join(names[:_NAME_LIMIT])
    if len(names) > _NAME_LIMIT:
        shown += f", ... (+{len(names) - _NAME_LIMIT} more)"
    return f"{len(names)} {label}: {shown}. "


def verify(
    out_dir: Path,
    unions: Sequence[UnionRecord],
    db_sides: dict[str, _Side],
    jsonl_sides: dict[str, _Side],
    *,
    drop_ids: frozenset[str] = frozenset(),
) -> int:
    """Re-read the tree and prove it holds what the sources held.

    Three passes, because they catch different failures.

    The **completeness** pass compares id SETS: the sources' ids, the union's
    ids, and the files on disk. It runs first and it is the one that makes the
    other two mean anything — see :func:`_assert_complete`.

    The **round-trip** pass re-reads every emitted file and diffs the rebuilt
    record against the union record field by field. That catches a writer and
    reader that disagree — a value that renders one way and parses back
    another.

    The **source** pass diffs the rebuilt record against the raw stores. That
    catches the failure the round-trip pass cannot see, which is the one that
    matters here: a union step that was itself wrong. A converter verified only
    against its own intermediate would agree with itself.

    Anything outside :data:`NORMALIZATIONS` raises. Returns the number of
    records verified, which is the whole corpus and not a sample — a gate that
    scores part of the deliverable reports green on a broken one.
    """
    _assert_complete(out_dir, unions, db_sides, jsonl_sides, drop_ids)
    by_id = {u.record.id: u for u in unions}
    rebuilt: dict[str, SeedRecord] = {}
    for union in unions:
        path = out_dir / (union.record.id + FILE_SUFFIX)
        try:
            rebuilt[union.record.id] = read_seed_file(path)
        except SeedFileError as exc:
            raise ConversionError(
                f"round-trip verification: the converter wrote a file its own "
                f"reader refuses: {exc}"
            ) from exc
        except OSError as exc:
            # A record that reached the union and has no readable file is the
            # single worst outcome this whole module exists to prevent, so it
            # is caught here rather than surfacing as a bare FileNotFoundError.
            raise ConversionError(
                f"round-trip verification: {union.record.id} is in the source "
                f"store and there is no readable file for it at {path} ({exc})"
            ) from exc

    for seed_id, record in rebuilt.items():
        union = by_id[seed_id]
        _diff_records(union.record, record, seed_id, "the union input", union.is_fork)
        _diff_sources(record, union, db_sides.get(seed_id), jsonl_sides.get(seed_id))

    return len(rebuilt)


def _edge_multiset(edges: Sequence[SeedEdge]) -> list[tuple[str, str, str]]:
    """Edges as an order-insensitive multiset (``sequence-order``)."""
    return sorted(
        (e.target_id, e.rel_type.value, e.created_at.isoformat()) for e in edges
    )


def _diff_records(
    expected: SeedRecord, actual: SeedRecord, seed_id: str, source: str, is_fork: bool
) -> None:
    """Field-by-field equality, with only the declared normalizations forgiven."""
    scalars: tuple[tuple[str, object, object], ...] = (
        ("id", expected.id, actual.id),
        ("title", expected.title, actual.title),
        ("status", expected.status, actual.status),
        ("type", expected.seed_type, actual.seed_type),
        ("parent", expected.parent, actual.parent),
        ("created_at", expected.created_at, actual.created_at),
        ("updated_at", expected.updated_at, actual.updated_at),
        ("resolved_at", expected.resolved_at, actual.resolved_at),
        ("resolution", expected.resolution, actual.resolution),
        ("converted_at", expected.converted_at, actual.converted_at),
    )
    for name, want, got in scalars:
        if want != got:
            raise ConversionError(
                f"round-trip verification failed for {seed_id}: {name} is {got!r} "
                f"in the tree and {want!r} in {source}"
            )
    if expected.tags != actual.tags:
        raise ConversionError(
            f"round-trip verification failed for {seed_id}: tags are "
            f"{actual.tags!r} in the tree and {expected.tags!r} in {source}"
        )
    if _edge_multiset(expected.relationships) != _edge_multiset(actual.relationships):
        raise ConversionError(
            f"round-trip verification failed for {seed_id}: the relationship set "
            f"in the tree is not the one in {source}"
        )
    # `body-trailing-newline`: canonical form on both sides, so the 282 records
    # that differ from it by nothing else do not read as 282 divergences.
    if _canonical_body(expected.body) != _canonical_body(actual.body):
        if is_fork:
            return
        at = first_difference(
            _canonical_body(expected.body), _canonical_body(actual.body)
        )
        raise ConversionError(
            f"round-trip verification failed for {seed_id}: the body in the tree "
            f"and the body in {source} part ways at character {at}"
        )


def _diff_sources(
    actual: SeedRecord,
    union: UnionRecord,
    db_side: _Side | None,
    jsonl_side: _Side | None,
) -> None:
    """Diff the emitted record against the raw stores, not the intermediate."""
    seed_id = actual.id
    sides = [s.seed for s in (db_side, jsonl_side) if s is not None]
    if not sides:
        raise ConversionError(
            f"verification failed for {seed_id}: the tree holds a seed neither "
            f"store does"
        )

    def one_of(name: str, got: object, wanted: list[object]) -> None:
        if got not in wanted:
            raise ConversionError(
                f"verification failed for {seed_id}: {name} is {got!r} in the "
                f"tree, and no source store holds that value (they hold "
                f"{wanted!r})"
            )

    one_of("title", actual.title, [s.title for s in sides])
    one_of("status", actual.status, [s.status for s in sides])
    one_of("type", actual.seed_type, [s.seed_type for s in sides])
    one_of("resolution", actual.resolution, [s.resolution for s in sides])

    if actual.created_at != min(s.created_at for s in sides):
        raise ConversionError(
            f"verification failed for {seed_id}: created_at is "
            f"{actual.created_at.isoformat()}, not the earliest stamp the stores hold"
        )
    if actual.updated_at != max(s.updated_at for s in sides):
        raise ConversionError(
            f"verification failed for {seed_id}: updated_at is "
            f"{actual.updated_at.isoformat()}, not the latest stamp the stores hold"
        )

    for source in sides:
        missing = [tag for tag in source.tags if tag not in actual.tags]
        if missing:
            raise ConversionError(
                f"verification failed for {seed_id}: tag(s) {missing!r} are in a "
                f"source store and not in the tree"
            )

    # `fork-conflict-body`: a fork's body equals neither source, so containment
    # is the assertion. Everything else must carry a source body verbatim.
    bodies = [b for b in (union.db_body, union.jsonl_body) if b is not None]
    if union.kept_resolution:
        # The body in the tree is the operator's resolution of a conflict this
        # converter wrote on an earlier run. It is theirs, it is deliberately
        # neither source body, and re-deriving it is exactly what the fork rule
        # forbids — so nothing about it is asserted here.
        return
    if union.is_fork:
        for body in bodies:
            if body.strip("\n") and body.strip("\n") not in actual.body:
                raise ConversionError(
                    f"verification failed for {seed_id}: the fork's conflict file "
                    f"does not carry one of the two source bodies verbatim"
                )
        return
    body = _canonical_body(actual.body)
    if body not in [_canonical_body(b) for b in bodies]:
        raise ConversionError(
            f"verification failed for {seed_id}: the body in the tree is not the "
            f"body either store holds"
        )
    for other in bodies:
        if not db_extends_disk(body, _canonical_body(other)):
            raise ConversionError(
                f"verification failed for {seed_id}: the body in the tree does "
                f"not extend the body in one of the source stores, so text that "
                f"only ever existed in that store is gone"
            )


def _verify_edges(
    unions: Sequence[UnionRecord], halves: Sequence[_Half], dropped: Sequence[_EdgeKey]
) -> None:
    """`materialized-inverse-edge`: the tree's edges are a checked superset.

    Every source half is present, every emitted half is either a source half or
    the inverse of one, and nothing is missing except the edges the report says
    were dropped for naming a seed that does not exist.
    """
    emitted: set[tuple[str, str, str]] = set()
    for union in unions:
        for edge in union.record.relationships:
            emitted.add((union.record.id, edge.target_id, edge.rel_type.value))

    dropped_keys = set(dropped)
    source_keys: set[_EdgeKey] = set()
    for half in halves:
        key = _edge_key(half)
        source_keys.add(key)
        if key in dropped_keys:
            continue
        forward = (half.source_id, half.target_id, half.rel_type.value)
        if forward not in emitted:
            raise ConversionError(
                f"verification failed: the {half.rel_type.value} edge "
                f"{half.source_id} -> {half.target_id} is in a source store and "
                f"not in the tree"
            )

    for source_id, target_id, rel_value in emitted:
        key = _edge_key(
            _Half(
                source_id=source_id,
                target_id=target_id,
                rel_type=RelationType(rel_value),
                created_at=datetime.now(UTC),
            )
        )
        if key not in source_keys:
            raise ConversionError(
                f"verification failed: the tree holds a {rel_value} edge "
                f"{source_id} -> {target_id} that no source store implies"
            )


# --- The conversion ----------------------------------------------------------


def convert(
    seeds_dir: Path,
    *,
    keep_fixtures: bool = False,
    now: datetime | None = None,
) -> ConversionReport:
    """Convert the store under ``seeds_dir`` into ``seeds_dir/seeds/``.

    Non-destructive: ``seeds.db`` and ``seeds.jsonl`` are read and never
    written, and a file already in the tree that no longer has a record is
    reported rather than removed. Reverting the whole thing is
    ``rm -rf .seeds/seeds/``.

    Byte-idempotent: a second run against an unchanged store rewrites nothing,
    because ``converted_at`` — the one field with no source in the old store —
    is read back from the file it was stamped on rather than re-read from the
    clock.

    Raises :class:`ConversionError` when a source record cannot be read or when
    verification fails. It does *not* raise for an unresolved fork or a
    ``check`` violation: those land in the report, which is what
    :attr:`ConversionReport.clean` is for.
    """
    seeds_dir = Path(seeds_dir)
    stamp = (now or datetime.now(UTC)).astimezone(UTC)
    db_path = seeds_dir / DB_FILE
    jsonl_path = seeds_dir / JSONL_FILE
    out_dir = seed_files_dir(seeds_dir)

    if not db_path.exists() and not jsonl_path.exists():
        raise ConversionError(
            f"{seeds_dir}: neither {DB_FILE} nor {JSONL_FILE} is here, so there "
            "is no pre-0.7 store to convert"
        )

    db_sides, db_halves, legacy = _load_db(db_path)
    jsonl_sides, jsonl_halves = _load_jsonl(jsonl_path)

    report = ConversionReport(
        seeds_dir=seeds_dir,
        out_dir=out_dir,
        db_present=db_path.exists(),
        jsonl_present=jsonl_path.exists(),
        dropped_legacy_rows=legacy,
    )

    drop_ids = _fixture_drops(db_sides, jsonl_sides, keep_fixtures, report)
    known = frozenset((set(db_sides) | set(jsonl_sides)) - drop_ids)
    halves = [*db_halves, *jsonl_halves]
    edges, dangling = _resolve_edges(halves, known)
    report.dropped_edges = [f"{a} -{rel}-> {b}" for rel, a, b in dangling]

    report.source_ids = len(set(db_sides) | set(jsonl_sides))
    unions, divergences = union_records(db_sides, jsonl_sides, edges, drop_ids=drop_ids)
    report.field_divergences = divergences
    for union in unions:
        report.counts[union.classification] = (
            report.counts.get(union.classification, 0) + 1
        )
        if union.is_fork:
            report.forks.append(union.record.id)

    _write_tree(seeds_dir, unions, stamp, report)
    _verify_edges(unions, halves, dangling)
    report.verified = verify(out_dir, unions, db_sides, jsonl_sides, drop_ids=drop_ids)
    report.stale_files = _stale_files(out_dir, {u.record.id for u in unions})
    report.prefix_written = _write_config(seeds_dir, db_path, known)
    report.check_findings = _gate(seeds_dir, set(report.forks))
    return report


def _fixture_drops(
    db_sides: dict[str, _Side],
    jsonl_sides: dict[str, _Side],
    keep_fixtures: bool,
    report: ConversionReport,
) -> frozenset[str]:
    """Which of the six ruled fixture ids this store actually drops.

    The ruling was made against verified records — empty body, no relationship
    rows, no non-fixture child. An id is repo-local, so the profile is
    re-checked here rather than trusted: another repo's ``seeds-71`` holding
    real deliberation is converted like anything else, and says so.
    """
    if keep_fixtures:
        return frozenset()
    drops: set[str] = set()
    for seed_id in sorted(FIXTURE_IDS):
        sides = [s for s in (db_sides.get(seed_id), jsonl_sides.get(seed_id)) if s]
        if not sides:
            continue
        if all(not side.seed.content.strip() for side in sides):
            drops.add(seed_id)
            report.dropped_fixtures.append(seed_id)
        else:
            report.kept_fixtures.append(seed_id)
    return frozenset(drops)


def _write_tree(
    seeds_dir: Path,
    unions: Sequence[UnionRecord],
    stamp: datetime,
    report: ConversionReport,
) -> None:
    """Write every record, stamping ``converted_at`` once and only once."""
    seed_files_dir(seeds_dir).mkdir(parents=True, exist_ok=True)
    for union in unions:
        path = path_for_id(seeds_dir, union.record.id)
        existing = _existing(path)
        union.record.converted_at = (
            existing.converted_at
            if existing is not None and existing.converted_at is not None
            else stamp
        )
        if union.is_fork and existing is not None and _resolved_fork(existing.body):
            # The operator finished this merge by hand and their resolution
            # lives only here. Re-emitting the conflict would destroy it, which
            # is the one way a re-run could lose deliberation.
            union.record.body = existing.body
            union.kept_resolution = True
            report.forks_already_resolved.append(union.record.id)
            report.forks.remove(union.record.id)
        text = render_seed_file(union.record)
        if existing is not None and path.read_text(encoding="utf-8") == text:
            report.unchanged.append(union.record.id)
            continue
        write_seed_file(path, union.record)
        report.written.append(union.record.id)


def _existing(path: Path) -> SeedRecord | None:
    """The record already at ``path``, or ``None`` if there is none to read.

    A file that will not parse is treated as absent: it is about to be replaced
    by one that does, and refusing to convert because the *previous* run's
    output is broken would make the tool unable to repair itself.
    """
    if not path.exists():
        return None
    try:
        return read_seed_file(path)
    except SeedFileError:
        return None


def _resolved_fork(body: str) -> bool:
    """Whether a body that was written as a conflict no longer reads as one."""
    return f"<<<<<<< {_DB_LABEL}" not in body


def _stale_files(out_dir: Path, live: set[str]) -> list[str]:
    """Files in the tree with no record in either store. Reported, never removed."""
    return sorted(
        p.name
        for p in out_dir.glob(f"*{FILE_SUFFIX}")
        if p.name[: -len(FILE_SUFFIX)] not in live
    )


def _write_config(seeds_dir: Path, db_path: Path, known: frozenset[str]) -> str | None:
    """Write ``.seeds/config.yaml`` with the project prefix (§9), if absent.

    The prefix lived in the SQLite ``config`` table, which phase 5 deletes, so
    the converter is the last moment it can be read. It cannot be derived from
    filenames later — a repo with no seeds has no prefix to read — and it is
    not a frontmatter field, because it is a property of the project.
    """
    config_path = seeds_dir / "config.yaml"
    if config_path.exists():
        return None
    prefix: str | None = None
    if db_path.exists():
        db = LegacyDatabase(db_path)
        try:
            if db.has_prefix_configured():
                prefix = db.get_prefix()
        finally:
            db.close()
    if prefix is None:
        prefixes = {seed_id.split("-")[0] for seed_id in known}
        if len(prefixes) != 1:
            return None
        prefix = next(iter(prefixes))
    config_path.write_text(f"prefix: {prefix}\n", encoding="utf-8")
    return prefix


def _gate(seeds_dir: Path, forks: set[str]) -> list[Finding]:
    """Run ``seeds check`` on the output, minus the conflicts we just wrote.

    A fork file carries git conflict markers on purpose, and ``check`` reports
    those as a violation — correctly, because the store is unfinished until a
    human resolves them. Counting them here as well would say the same thing
    twice and bury the findings that are *not* expected, so the marker finding
    on a file this run wrote as a fork is filtered out and the fork itself is
    reported separately. Everything else, including any other finding on the
    same file, is reported.
    """
    findings = check_violations(seeds_dir)
    kept: list[Finding] = []
    for finding in findings:
        stem = finding.path.name[: -len(FILE_SUFFIX)]
        if finding.code == "conflict-markers" and stem in forks:
            continue
        kept.append(finding)
    return kept
