"""seeds export functionality."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from seeds.db import SEEDS_DIR, Database
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
)

JSONL_FILE = "seeds.jsonl"


@dataclass
class ImportResult:
    """Outcome counts from a JSONL import.

    - ``created``: seeds whose ID was absent from the DB and were inserted.
    - ``updated``: existing seeds overwritten because the JSONL record's
      ``updated_at`` was newer than the DB's (last-write-wins).
    - ``skipped``: records left untouched — an existing seed whose JSONL
      ``updated_at`` was not newer than the DB's (stale or identical), or a
      legacy v1 collision (v1 import is create-only).
    """

    created: int = 0
    updated: int = 0
    skipped: int = 0

    @property
    def total(self) -> int:
        """Total records processed (created + updated + skipped)."""
        return self.created + self.updated + self.skipped


def _datetime_to_str(dt: datetime | None) -> str | None:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat()


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
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        resolved_at=(
            datetime.fromisoformat(data["resolved_at"])
            if data.get("resolved_at")
            else None
        ),
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
        resolved_at = (
            datetime.fromisoformat(q_data["answered_at"])
            if q_data.get("answered_at")
            else None
        )
        q_seed = Seed(
            id=q_seed_id,
            title=q_data["text"],
            content=q_data.get("answer") or "",
            status=seed_status,
            seed_type=SeedType.QUESTION,
            created_at=datetime.fromisoformat(q_data["created_at"]),
            updated_at=datetime.fromisoformat(q_data["created_at"]),
            resolved_at=resolved_at,
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
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        resolved_at=(
            datetime.fromisoformat(data["resolved_at"])
            if data.get("resolved_at")
            else None
        ),
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
        created_at = (
            datetime.fromisoformat(rel_data["created_at"])
            if rel_data.get("created_at")
            else None
        )
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


def import_records(db: Database, records: Iterable[dict[str, Any]]) -> ImportResult:
    """Import already-parsed JSONL records into the database.

    Detects format version per record (v2 has ``format_version: 2``; anything
    else is treated as legacy v1) and applies it via the matching importer.
    Tallies the per-record outcomes into an :class:`ImportResult`.
    """
    result = ImportResult()
    for data in records:
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


def import_lines(db: Database, lines: Iterable[str]) -> ImportResult:
    """Import seeds from an iterable of JSONL lines (e.g. a file or stdin).

    Blank lines are ignored. This is the seam the CLI can feed stdin through
    without first materializing a file on disk.
    """
    return import_records(db, _iter_records(lines))


def import_from_jsonl(db: Database, input_path: Path | None = None) -> ImportResult:
    """Import seeds from a JSONL file using UPSERT / last-write-wins semantics.

    Detects format version automatically per record:
    - v1: has 'related_to' array and embedded 'questions' (create-only)
    - v2: has 'format_version: 2' and 'relationships' array (LWW upsert)

    Args:
        db: Database instance
        input_path: Path to input file. If None, uses .seeds/seeds.jsonl

    Returns:
        An :class:`ImportResult` with created/updated/skipped counts. A missing
        file yields an empty result (all-zero counts).
    """
    if input_path is None:
        input_path = Path.cwd() / SEEDS_DIR / JSONL_FILE

    if not input_path.exists():
        return ImportResult()

    with open(input_path) as f:
        return import_lines(db, f)
