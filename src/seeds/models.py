"""seeds data models."""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
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


# Default project prefix for sequential IDs
DEFAULT_PREFIX = "seeds"


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
class Relationship:
    """A typed, directed relationship between two seeds."""

    source_id: str
    target_id: str
    rel_type: RelationType = RelationType.RELATES_TO
    created_at: datetime = field(default_factory=now_utc)
