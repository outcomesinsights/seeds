"""seeds export functionality."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from seeds.db import SEEDS_DIR, Database, recover_prefix_from_id
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    now_utc,
)

JSONL_FILE = "seeds.jsonl"

# How far ahead of local time a record's ``updated_at`` may be and still be
# imported. Machines really do disagree about the time, so zero tolerance would
# reject legitimate records from a slightly-fast peer; a few minutes covers
# ordinary skew without covering a corrupt or forged timestamp.
#
# Anything further ahead is refused, because importing it poisons the seed
# permanently: the import picks a winner by comparing ``updated_at``, but a
# later legitimate local edit stamps ``now_utc()`` (db.update_seed), which is
# EARLIER than a future date. The seed's timestamp moves backward, the file's
# record keeps out-ranking every subsequent edit, and each re-import of that
# same unchanged file destroys whatever was written since.
FUTURE_TIMESTAMP_TOLERANCE = timedelta(minutes=5)


@dataclass(frozen=True)
class RefusedRecord:
    """A record the import declined to apply, and why.

    ``claimed_updated_at`` is the raw string the file asserted, reported
    verbatim so the operator can see exactly what is wrong upstream.
    """

    seed_id: str
    claimed_updated_at: str
    reason: str


@dataclass
class ImportResult:
    """Outcome counts from a JSONL import.

    - ``created``: seeds whose ID was absent from the DB and were inserted.
    - ``updated``: existing seeds overwritten because the JSONL record's
      ``updated_at`` was newer than the DB's (last-write-wins).
    - ``skipped``: records left untouched — an existing seed whose JSONL
      ``updated_at`` was not newer than the DB's (stale or identical), or a
      legacy v1 collision (v1 import is create-only).
    - ``refused``: records rejected outright without touching the DB at all
      (not even their relationships), because their ``updated_at`` is further
      ahead of local time than :data:`FUTURE_TIMESTAMP_TOLERANCE` allows.
    """

    created: int = 0
    updated: int = 0
    skipped: int = 0
    refused: list[RefusedRecord] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total records processed (created + updated + skipped + refused)."""
        return self.created + self.updated + self.skipped + len(self.refused)


def _datetime_to_str(dt: datetime | None) -> str | None:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat()


def _parse_timestamp(value: str) -> datetime:
    """Parse an ISO timestamp from a JSONL record; treat a naive one as UTC.

    Records are supposed to carry timezone-aware timestamps, but a hand-edited
    or third-party-generated file can drop the offset. A naive value used to
    reach the last-write-wins comparison as-is and raise
    ``TypeError: can't compare offset-naive and offset-aware datetimes``,
    aborting the import mid-file with the records before it already committed
    and no summary printed.

    Chosen resolution: interpret naive input as UTC rather than rejecting the
    record. Reasons:

    - It is what seeds already does elsewhere for naive ISO input
      (``parse_since`` in models.py), so the file format has one rule, not two.
    - It never loses the record. Dropping a timezone is a transcription slip,
      not evidence that the content is wrong.
    - It composes safely with the future-timestamp refusal below. If the naive
      value was really a *local* wall clock from a machine east of UTC,
      reading it as UTC places it in the future, where the refusal catches it;
      west of UTC it reads as older than it is and simply loses the
      last-write-wins comparison. Neither direction can silently overwrite a
      fresher DB row.
    """
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _optional_timestamp(value: str | None) -> datetime | None:
    """Parse an optional ISO timestamp field (``None``/empty stays ``None``)."""
    if not value:
        return None
    return _parse_timestamp(value)


def _refusal_for(data: dict[str, Any], now: datetime) -> RefusedRecord | None:
    """Return a :class:`RefusedRecord` if this record's timestamp is untrustworthy.

    Applies to every record regardless of format version: the claim being
    checked is the file's ``updated_at``, which both the v1 and v2 importers
    write into the DB verbatim.
    """
    claimed = data["updated_at"]
    if _parse_timestamp(claimed) <= now + FUTURE_TIMESTAMP_TOLERANCE:
        return None
    return RefusedRecord(
        seed_id=data["id"],
        claimed_updated_at=claimed,
        reason=(
            f"updated_at is more than {FUTURE_TIMESTAMP_TOLERANCE} ahead of "
            f"now ({now.isoformat()})"
        ),
    )


def seed_to_dict(seed: Seed, db: Database) -> dict[str, Any]:
    """Convert a seed and its outbound relationships to a dictionary for export."""
    # Get outbound relationships for this seed
    rels = db.get_relationships(seed.id, direction="outbound")

    return {
        "format_version": 2,
        "id": seed.id,
        "title": seed.title,
        "content": seed.content,
        "status": seed.status.value,
        "seed_type": seed.seed_type,
        "tags": seed.tags,
        "created_at": _datetime_to_str(seed.created_at),
        "updated_at": _datetime_to_str(seed.updated_at),
        "resolved_at": _datetime_to_str(seed.resolved_at),
        "resolution": seed.resolution,
        "relationships": [
            {
                "target_id": r.target_id,
                "rel_type": r.rel_type.value,
                "created_at": _datetime_to_str(r.created_at),
            }
            for r in rels
        ],
    }


# How much of a divergent body to show in the refusal. Enough to recognise
# which deliberation is at stake; the file itself has the rest.
EXCERPT_LIMIT = 200

DivergenceKind = Literal["missing", "content", "unreadable"]


@dataclass(frozen=True)
class Divergence:
    """An on-disk JSONL record the export would destroy, that the DB never saw.

    - ``missing``: the record is on disk and the database has no such seed, so
      rewriting the file from the database would simply delete it.
    - ``content``: the seed exists in both, but the database's body does not
      begin with the on-disk body (see :func:`db_extends_disk`), so overwriting
      would drop text that only ever existed in the file.
    - ``unreadable``: the line is not valid JSON — most often unresolved git
      conflict markers. Nothing can be said about what it holds, which is
      exactly why it must not be overwritten.

    ``seed_id`` is the record's ``id``, or ``"<line N>"`` for an ``unreadable``
    line where no ID could be read. Either way it locates the record.
    """

    seed_id: str
    kind: DivergenceKind
    detail: str
    on_disk: str = ""
    in_db: str = ""


class DivergentExportError(Exception):
    """Raised instead of overwriting JSONL records the database never saw.

    Carries the full :class:`Divergence` list so the CLI can name every
    affected seed. The file is untouched when this is raised.
    """

    def __init__(self, output_path: Path, divergences: list[Divergence]) -> None:
        self.output_path = output_path
        self.divergences = divergences
        super().__init__(
            f"{output_path} holds {len(divergences)} record(s) the database has "
            "never seen; exporting would destroy them"
        )


def db_extends_disk(db_content: str, disk_content: str) -> bool:
    """Does the database's content begin with the on-disk content?

    Divergence is decided on CONTENT, never on ``updated_at``. Timestamps only
    answer "which is newer", and they are the input already known to be
    untrustworthy (clock skew, hand edits, merge resolutions). The question
    that actually matters before a destructive rewrite is "does the disk hold
    text the database has never seen", which is a content question.

    A flat "content differs -> refuse" would be unusable: the database is
    normally *ahead* of the file, which is the whole reason to flush. The test
    that separates "ahead" from "diverged" leans on ``seeds update -a`` being
    the normal editing verb for a seed body:

    - identical bodies -> nothing to lose.
    - the database's body **starts with** the file's -> the database is the
      file's version plus appends; overwriting loses nothing.
    - anything else -> the file holds text the database never had. Refuse.

    Validated against this project's own JSONL history: of 42 content-changing
    edits across 67 commits, 41 were literal appends. The single exception was
    an in-place rewrite that prepended a header to an existing body — precisely
    the kind of edit an operator should be told about.

    The stripped fallback exists because ``seeds update -a`` strips the
    *combined* body (cli.py), so appending to a body with leading whitespace
    yields a result that is not a literal prefix of it even though no text was
    lost. Whitespace is not deliberation. It cannot mask real loss: any actual
    character present on disk and absent from the database still fails.
    """
    if db_content.startswith(disk_content):
        return True
    return db_content.strip().startswith(disk_content.strip())


def first_difference(db_content: str, disk_content: str) -> int:
    """Index of the first character where the two bodies part ways.

    ``strict=False`` is deliberate: the two bodies routinely differ in length
    — one being a prefix of the other is the common, benign case — so zip must
    stop at the shorter. The fallback below reports that shared length as the
    divergence point.
    """
    for i, (a, b) in enumerate(zip(db_content, disk_content, strict=False)):
        if a != b:
            return i
    return min(len(db_content), len(disk_content))


def _excerpt(text: str) -> str:
    """One-line, quoted, length-capped rendering of a body for the refusal."""
    if len(text) <= EXCERPT_LIMIT:
        return repr(text)
    return f"{text[:EXCERPT_LIMIT]!r}... (+{len(text) - EXCERPT_LIMIT} more chars)"


def find_divergence(db: Database, output_path: Path) -> list[Divergence]:
    """Find records in ``output_path`` that rewriting it from ``db`` would destroy.

    Read-only. Returns an empty list when the file is absent or when every
    record on disk is accounted for by the database.

    Scope: whole records (present on disk, absent from the database) and the
    ``content`` field. Title, tags, status and resolution are deliberately NOT
    guarded — replacement is their normal verb (``seeds update --title``,
    ``--tags``, ``seeds resolve``, ``seeds trellis`` all overwrite in place), so
    guarding them would refuse ordinary local editing. ``content`` is the field
    that accumulates deliberation, and the one this tool exists to not lose.

    Records are checked in file order without de-duplicating IDs, so a botched
    merge that left two lines for the same seed is judged line by line.
    """
    if not output_path.exists():
        return []

    in_db = {seed.id: seed.content for seed in db.list_seeds(include_terminal=True)}

    divergences: list[Divergence] = []
    with open(output_path) as f:
        for lineno, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                divergences.append(
                    Divergence(
                        seed_id=f"<line {lineno}>",
                        kind="unreadable",
                        detail=(
                            f"line {lineno} is not valid JSON ({exc.msg}) — "
                            "unresolved merge conflict markers are the usual cause"
                        ),
                        on_disk=_excerpt(raw.strip()),
                    )
                )
                continue

            seed_id = data.get("id")
            if seed_id is None:
                divergences.append(
                    Divergence(
                        seed_id=f"<line {lineno}>",
                        kind="unreadable",
                        detail=f"line {lineno} is a JSON record with no 'id' field",
                        on_disk=_excerpt(raw.strip()),
                    )
                )
                continue

            if seed_id not in in_db:
                divergences.append(
                    Divergence(
                        seed_id=seed_id,
                        kind="missing",
                        detail=(
                            "present on disk, absent from the database — "
                            "rewriting the file would delete this record"
                        ),
                        on_disk=_excerpt(data.get("content") or ""),
                    )
                )
                continue

            disk_content = data.get("content") or ""
            db_content = in_db[seed_id]
            if db_extends_disk(db_content, disk_content):
                continue

            divergences.append(
                Divergence(
                    seed_id=seed_id,
                    kind="content",
                    detail=(
                        "the database's content does not begin with the "
                        "on-disk content (they diverge at character "
                        f"{first_difference(db_content, disk_content)})"
                    ),
                    on_disk=_excerpt(disk_content),
                    in_db=_excerpt(db_content),
                )
            )

    return divergences


def _render_jsonl(db: Database) -> str:
    """Serialize every seed exactly as ``export_to_jsonl`` would write them.

    Shared by the writer and :func:`export_would_change` so the two can never
    disagree about what "the same content" means.
    """
    seeds = db.list_seeds(include_terminal=True)
    seeds.sort(key=lambda s: s.id)
    return "".join(
        json.dumps(seed_to_dict(seed, db), ensure_ascii=False) + "\n" for seed in seeds
    )


def export_would_change(db: Database, output_path: Path | None = None) -> bool:
    """Would exporting ``db`` to ``output_path`` change what's on disk?

    Read-only: renders the exact bytes :func:`export_to_jsonl` would write and
    compares them to the file's current content. A missing file counts as a
    change — there's nothing for a fresh write to be a no-op against.

    Used by ``seeds sync`` (seeds-ww8) to tell an ordinary flush — nothing
    pending, harmless next to whatever else is staged — from one that would
    actually rewrite the file and so risks baking unrelated database changes
    into someone else's commit.

    Deliberately blind to the divergence guard: this answers "would the bytes
    differ", not "is overwriting them safe". A divergent file renders
    differently too, so this returns True for it as well; the safety call
    itself stays :func:`find_divergence`'s job alone.
    """
    if output_path is None:
        output_path = Path.cwd() / SEEDS_DIR / JSONL_FILE
    if not output_path.exists():
        return True
    return output_path.read_text() != _render_jsonl(db)


def export_to_jsonl(
    db: Database,
    output_path: Path | None = None,
    *,
    allow_divergence: bool = False,
) -> Path:
    """Export all seeds to JSONL format (v2 with relationships).

    The file is rewritten wholesale from the database, so it is checked first:
    any record on disk that the database cannot account for
    (:func:`find_divergence`) raises :class:`DivergentExportError` and nothing
    is written. Refusing is deliberate — see the parent decision on seeds-agk:
    auto-merging divergent bodies invents a resolution nobody reviews, and a
    sidecar backup is a consolation prize for still destroying the file. The
    JSONL is git-tracked; the operator resolves it.

    Guarding is the default so no future call site can forget it. Pass
    ``allow_divergence=True`` only where the whole-file rewrite *is* the point
    and the divergence is self-inflicted and already reported — currently only
    ``seeds rename-prefix``, which renumbers every ID at once.

    Args:
        db: Database instance
        output_path: Path to output file. If None, uses .seeds/seeds.jsonl
        allow_divergence: Skip the guard and overwrite unconditionally.

    Returns:
        Path to the output file

    Raises:
        DivergentExportError: The file holds records the database never saw.
    """
    if output_path is None:
        output_path = Path.cwd() / SEEDS_DIR / JSONL_FILE

    if not allow_divergence:
        divergences = find_divergence(db, output_path)
        if divergences:
            raise DivergentExportError(output_path, divergences)

    with open(output_path, "w") as f:
        f.write(_render_jsonl(db))

    return output_path


def _import_v1_record(db: Database, data: dict[str, Any]) -> str:
    """Import a v1 format record (embedded questions, related_to array).

    Legacy/create-only: returns ``"created"`` when the seed was inserted, or
    ``"skipped"`` when a seed with this ID already exists. v1 records are never
    used to overwrite an existing seed.
    """
    # Check if seed exists
    if db.get_seed(data["id"]):
        return "skipped"

    # Create seed (v1 had related_to on the seed object, now handled via relationships)
    seed = Seed(
        id=data["id"],
        title=data["title"],
        content=data.get("content", ""),
        status=SeedStatus(data["status"]),
        seed_type=data["seed_type"],
        tags=data.get("tags", []),
        created_at=_parse_timestamp(data["created_at"]),
        updated_at=_parse_timestamp(data["updated_at"]),
        resolved_at=_optional_timestamp(data.get("resolved_at")),
        resolution=data.get("resolution", ""),
    )
    db.create_seed(seed)

    # Convert related_to to relationships
    for related_id in data.get("related_to", []):
        db.create_relationship(data["id"], related_id, RelationType.RELATES_TO)

    # Convert embedded questions to question-seeds + relationships
    for q_data in data.get("questions", []):
        q_status = q_data.get("status", "open")
        if q_status == "open":
            seed_status = SeedStatus.CAPTURED
        elif q_status == "answered":
            seed_status = SeedStatus.RESOLVED
        elif q_status == "deferred":
            seed_status = SeedStatus.DEFERRED
        else:
            seed_status = SeedStatus.CAPTURED

        q_seed_id = db.next_id()
        q_created_at = _parse_timestamp(q_data["created_at"])
        q_seed = Seed(
            id=q_seed_id,
            title=q_data["text"],
            content=q_data.get("answer") or "",
            status=seed_status,
            seed_type=SeedType.QUESTION.value,
            created_at=q_created_at,
            updated_at=q_created_at,
            resolved_at=_optional_timestamp(q_data.get("answered_at")),
        )
        db.create_seed(q_seed)
        db.create_relationship(q_seed_id, data["id"], RelationType.QUESTIONS)

    return "created"


def _seed_from_v2(data: dict[str, Any]) -> Seed:
    """Build a Seed from a v2 record's scalar fields (no relationships)."""
    return Seed(
        id=data["id"],
        title=data["title"],
        content=data.get("content", ""),
        status=SeedStatus(data["status"]),
        seed_type=data["seed_type"],
        tags=data.get("tags", []),
        created_at=_parse_timestamp(data["created_at"]),
        updated_at=_parse_timestamp(data["updated_at"]),
        resolved_at=_optional_timestamp(data.get("resolved_at")),
        resolution=data.get("resolution", ""),
    )


def _assert_v2_relationships(db: Database, data: dict[str, Any]) -> None:
    """Re-assert a v2 record's outbound edges (idempotent via INSERT OR IGNORE).

    An edge may reference a target that appears later in the file; there is no
    FK enforcement, so out-of-order targets are fine. Re-import never
    duplicates edges because of the UNIQUE(source, target, rel_type) constraint.
    """
    for rel_data in data.get("relationships", []):
        rel_type = RelationType(rel_data["rel_type"])
        created_at = _optional_timestamp(rel_data.get("created_at"))
        db.create_relationship(data["id"], rel_data["target_id"], rel_type, created_at)


def _import_v2_record(db: Database, data: dict[str, Any]) -> str:
    """Import a v2 format record (relationships as outbound edges).

    UPSERT with last-write-wins on ``updated_at``:
    - New ID -> insert. Returns ``"created"``.
    - Existing ID, JSONL ``updated_at`` strictly newer than the DB's ->
      overwrite (timestamp written verbatim). Returns ``"updated"``.
    - Existing ID, JSONL ``updated_at`` not newer -> leave the DB row alone.
      Returns ``"skipped"``.

    Relationships are re-asserted idempotently in every case, so a stale or
    skipped seed still backfills any missing edges without duplicating them.
    Records present in the DB but absent from the JSONL are never deleted.
    """
    seed = _seed_from_v2(data)
    existing = db.get_seed(seed.id)

    if existing is None:
        db.create_seed(seed)
        _assert_v2_relationships(db, data)
        return "created"

    if seed.updated_at > existing.updated_at:
        # Last-write-wins: JSONL is fresher. Preserve its updated_at verbatim
        # (touch=False) so the timestamp signal survives the round-trip.
        db.update_seed(seed, touch=False)
        _assert_v2_relationships(db, data)
        return "updated"

    # DB row is as-fresh-or-fresher: don't clobber it. Still backfill edges.
    _assert_v2_relationships(db, data)
    return "skipped"


def _iter_records(lines: Iterable[str]) -> Iterable[dict[str, Any]]:
    """Parse a stream of JSONL lines into records, skipping blank lines."""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        yield json.loads(line)


def _bootstrap_db_if_absent(db: Database, records: list[dict[str, Any]]) -> None:
    """Create the schema + recover the prefix when the DB file is absent.

    The fresh-clone rehydration case: a checkout ships ``.seeds/seeds.jsonl``
    but the DB is gitignored, and the project prefix lives only in the
    gitignored DB config. Rather than erroring "run seeds init" or inheriting a
    wrong directory-derived prefix, recover the prefix from the first record's
    ID (e.g. ``seeds-155`` -> ``seeds``) and write it to config as part of
    ``init``.

    No-op when the DB file already exists (existing initialized projects are
    untouched) or when ``records`` is empty (nothing to recover a prefix from;
    ``init`` would leave the prefix unset, which the import has no IDs to need).
    Recovery falls back to leaving the prefix unset (``init()`` with no prefix)
    when the first record's ID is not a recoverable ``<prefix>-<number>``
    shape, so a legacy-only export still bootstraps a usable DB.
    """
    if db.is_initialized():
        return
    prefix: str | None = None
    if records:
        prefix = recover_prefix_from_id(records[0]["id"])
    db.init(prefix=prefix)


def import_records(
    db: Database,
    records: Iterable[dict[str, Any]],
    bootstrap: bool = False,
) -> ImportResult:
    """Import already-parsed JSONL records into the database.

    Detects format version per record (v2 has ``format_version: 2``; anything
    else is treated as legacy v1) and applies it via the matching importer.
    Tallies the per-record outcomes into an :class:`ImportResult`.

    A record whose ``updated_at`` is further ahead of local time than
    :data:`FUTURE_TIMESTAMP_TOLERANCE` is refused before either importer sees
    it — nothing about it reaches the DB, not even its relationships — and is
    recorded in ``result.refused`` for the caller to report. Every record is
    compared against a single ``now`` captured once, so a long import cannot
    change its mind partway through.

    When ``bootstrap`` is True and the database file does not yet exist, the
    schema is created and the project prefix is recovered from the first
    record's ID before importing (fresh-clone rehydration). ``records`` is
    materialized into a list in that case so the first ID can be peeked.
    Existing initialized databases are imported into unchanged regardless of
    ``bootstrap``.
    """
    if bootstrap:
        records = list(records)
        _bootstrap_db_if_absent(db, records)

    now = now_utc()
    result = ImportResult()
    for data in records:
        refusal = _refusal_for(data, now)
        if refusal is not None:
            result.refused.append(refusal)
            continue

        if data.get("format_version") == 2:
            outcome = _import_v2_record(db, data)
        else:
            outcome = _import_v1_record(db, data)

        if outcome == "created":
            result.created += 1
        elif outcome == "updated":
            result.updated += 1
        else:
            result.skipped += 1

    return result


def import_lines(
    db: Database, lines: Iterable[str], bootstrap: bool = False
) -> ImportResult:
    """Import seeds from an iterable of JSONL lines (e.g. a file or stdin).

    Blank lines are ignored. This is the seam the CLI can feed stdin through
    without first materializing a file on disk.

    Pass ``bootstrap=True`` to create the schema and recover the project
    prefix from the first record when the DB file is absent (fresh-clone
    rehydration); see :func:`import_records`.
    """
    return import_records(db, _iter_records(lines), bootstrap=bootstrap)


def import_from_jsonl(
    db: Database, input_path: Path | None = None, bootstrap: bool = False
) -> ImportResult:
    """Import seeds from a JSONL file using UPSERT / last-write-wins semantics.

    Detects format version automatically per record:
    - v1: has 'related_to' array and embedded 'questions' (create-only)
    - v2: has 'format_version: 2' and 'relationships' array (LWW upsert)

    Args:
        db: Database instance
        input_path: Path to input file. If None, uses .seeds/seeds.jsonl
        bootstrap: When True and the DB file is absent, create the schema and
            recover the project prefix from the first record's ID before
            importing (fresh-clone rehydration). Defaults to False so existing
            initialized projects are unaffected.

    Returns:
        An :class:`ImportResult` with created/updated/skipped counts plus any
        records refused for an untrustworthy ``updated_at``. A missing file
        yields an empty result (all-zero counts).
    """
    if input_path is None:
        input_path = Path.cwd() / SEEDS_DIR / JSONL_FILE

    if not input_path.exists():
        return ImportResult()

    with open(input_path) as f:
        return import_lines(db, f, bootstrap=bootstrap)
