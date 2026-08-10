"""seeds export functionality."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

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
        "seed_type": seed.seed_type.value,
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


def export_to_jsonl(db: Database, output_path: Path | None = None) -> Path:
    """Export all seeds to JSONL format (v2 with relationships).

    Args:
        db: Database instance
        output_path: Path to output file. If None, uses .seeds/seeds.jsonl

    Returns:
        Path to the output file
    """
    if output_path is None:
        output_path = Path.cwd() / SEEDS_DIR / JSONL_FILE

    # Get all seeds (including terminal states)
    seeds = db.list_seeds(include_terminal=True)

    # Sort by ID for consistent output
    seeds.sort(key=lambda s: s.id)

    # Write JSONL
    with open(output_path, "w") as f:
        for seed in seeds:
            data = seed_to_dict(seed, db)
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

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
        seed_type=SeedType(data["seed_type"]),
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
            seed_type=SeedType.QUESTION,
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
        seed_type=SeedType(data["seed_type"]),
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
