"""seeds export functionality."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from seeds.db import SEEDS_DIR, Database
from seeds.models import (
    RelationType,
    Seed,
    SeedStatus,
    SeedType,
    generate_id,
)

JSONL_FILE = "seeds.jsonl"


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


def _import_v1_record(db: Database, data: dict[str, Any]) -> bool:
    """Import a v1 format record (embedded questions, related_to array).

    Returns True if a seed was imported.
    """
    # Check if seed exists
    if db.get_seed(data["id"]):
        return False

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

        q_seed_id = generate_id("seeds")
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

    return True


def _import_v2_record(db: Database, data: dict[str, Any]) -> bool:
    """Import a v2 format record (relationships as outbound edges).

    Returns True if a seed was imported.
    """
    if db.get_seed(data["id"]):
        return False

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

    # Create relationships from outbound edges
    for rel_data in data.get("relationships", []):
        rel_type = RelationType(rel_data["rel_type"])
        created_at = (
            datetime.fromisoformat(rel_data["created_at"])
            if rel_data.get("created_at")
            else None
        )
        db.create_relationship(
            data["id"], rel_data["target_id"], rel_type, created_at
        )

    return True


def import_from_jsonl(db: Database, input_path: Path | None = None) -> int:
    """Import seeds from JSONL format.

    Detects format version automatically:
    - v1: has 'related_to' array and embedded 'questions'
    - v2: has 'format_version: 2' and 'relationships' array

    Args:
        db: Database instance
        input_path: Path to input file. If None, uses .seeds/seeds.jsonl

    Returns:
        Number of seeds imported
    """
    if input_path is None:
        input_path = Path.cwd() / SEEDS_DIR / JSONL_FILE

    if not input_path.exists():
        return 0

    count = 0
    with open(input_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            data = json.loads(line)

            # Detect format version
            if data.get("format_version") == 2:
                imported = _import_v2_record(db, data)
            else:
                imported = _import_v1_record(db, data)

            if imported:
                count += 1

    return count
