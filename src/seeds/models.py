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


class QuestionStatus(Enum):
    """States for a question attached to a seed."""

    OPEN = "open"  # Needs an answer
    ANSWERED = "answered"  # Has been answered
    DEFERRED = "deferred"  # Postponed for later


def generate_id(prefix: str = "seed") -> str:
    """Generate a short hash-based ID like 'seed-a1b2'.

    Uses current time and random bytes to ensure uniqueness.
    """
    data = f"{time.time_ns()}{os.urandom(8).hex()}"
    hash_val = hashlib.sha256(data.encode()).hexdigest()[:4]
    return f"{prefix}-{hash_val}"


def generate_child_id(parent_id: str) -> str:
    """Generate a child ID from a parent ID.

    For example, if parent is 'seed-a1b2', this might return 'seed-a1b2.1'.
    The actual number is determined by the database layer based on existing children.
    """
    # This is a placeholder - actual implementation needs DB context
    # to determine the next child number
    return f"{parent_id}.1"


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
    related_to: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)
    resolved_at: datetime | None = None

    @property
    def parent_id(self) -> str | None:
        """Get parent ID from hierarchical ID."""
        return get_parent_id(self.id)

    def is_terminal(self) -> bool:
        """Check if seed is in a terminal state (resolved or abandoned)."""
        return self.status in (SeedStatus.RESOLVED, SeedStatus.ABANDONED)


@dataclass
class Question:
    """A question attached to a seed."""

    id: str
    seed_id: str
    text: str
    answer: str | None = None
    status: QuestionStatus = QuestionStatus.OPEN
    created_at: datetime = field(default_factory=now_utc)
    answered_at: datetime | None = None
