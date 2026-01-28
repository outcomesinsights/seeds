"""seeds export functionality."""

import json
from datetime import datetime
from pathlib import Path

from seeds.db import Database, SEEDS_DIR
from seeds.models import Seed, Question, SeedStatus, SeedType, QuestionStatus


JSONL_FILE = "seeds.jsonl"


def _datetime_to_str(dt: datetime | None) -> str | None:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat()


def seed_to_dict(seed: Seed, questions: list[Question]) -> dict:
    """Convert a seed and its questions to a dictionary for export."""
    return {
        "id": seed.id,
        "title": seed.title,
        "content": seed.content,
        "status": seed.status.value,
        "seed_type": seed.seed_type.value,
        "tags": seed.tags,
        "related_to": seed.related_to,
        "created_at": _datetime_to_str(seed.created_at),
        "updated_at": _datetime_to_str(seed.updated_at),
        "resolved_at": _datetime_to_str(seed.resolved_at),
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "answer": q.answer,
                "status": q.status.value,
                "created_at": _datetime_to_str(q.created_at),
                "answered_at": _datetime_to_str(q.answered_at),
            }
            for q in questions
        ],
    }


def export_to_jsonl(db: Database, output_path: Path | None = None) -> Path:
    """Export all seeds to JSONL format.

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
            questions = db.list_questions(seed_id=seed.id)
            data = seed_to_dict(seed, questions)
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    return output_path


def import_from_jsonl(db: Database, input_path: Path | None = None) -> int:
    """Import seeds from JSONL format.

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

            # Check if seed exists
            existing = db.get_seed(data["id"])
            if existing:
                # Skip existing seeds (could add merge logic later)
                continue

            # Create seed
            seed = Seed(
                id=data["id"],
                title=data["title"],
                content=data.get("content", ""),
                status=SeedStatus(data["status"]),
                seed_type=SeedType(data["seed_type"]),
                tags=data.get("tags", []),
                related_to=data.get("related_to", []),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
                resolved_at=(
                    datetime.fromisoformat(data["resolved_at"])
                    if data.get("resolved_at")
                    else None
                ),
            )
            db.create_seed(seed)
            count += 1

            # Create questions
            for q_data in data.get("questions", []):
                question = Question(
                    id=q_data["id"],
                    seed_id=data["id"],
                    text=q_data["text"],
                    answer=q_data.get("answer"),
                    status=QuestionStatus(q_data["status"]),
                    created_at=datetime.fromisoformat(q_data["created_at"]),
                    answered_at=(
                        datetime.fromisoformat(q_data["answered_at"])
                        if q_data.get("answered_at")
                        else None
                    ),
                )
                db.create_question(question)

    return count
