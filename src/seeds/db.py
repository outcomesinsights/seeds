"""seeds SQLite database layer."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from seeds.models import (
    Question,
    QuestionStatus,
    Seed,
    SeedStatus,
    SeedType,
    generate_id,
    get_parent_id,
    now_utc,
)

# Allow override via environment variable for testing/development
SEEDS_DIR = os.environ.get("SEEDS_DIR", ".seeds")
DB_FILE = "seeds.db"

# Gitignore template for .seeds/ directory (following beads' pattern).
# Ignores SQLite DB and runtime files; JSONL is tracked by git by default.
SEEDS_GITIGNORE = """\
# SQLite databases
*.db
*.db-journal
*.db-wal
*.db-shm
"""


def find_seeds_dir() -> Path | None:
    """Find the .seeds directory by walking up the directory tree.

    Returns the path to the .seeds directory if found, None otherwise.
    Searches from current directory up to filesystem root.
    """
    current = Path.cwd()
    while True:
        seeds_dir = current / SEEDS_DIR
        if seeds_dir.is_dir():
            return seeds_dir
        parent = current.parent
        if parent == current:
            # Reached filesystem root
            return None
        current = parent


SCHEMA = """
CREATE TABLE IF NOT EXISTS seeds (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    content TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'captured',
    seed_type TEXT NOT NULL DEFAULT 'idea',
    tags TEXT DEFAULT '[]',
    related_to TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    resolved_at TEXT
);

CREATE TABLE IF NOT EXISTS questions (
    id TEXT PRIMARY KEY,
    seed_id TEXT NOT NULL,
    text TEXT NOT NULL,
    answer TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    answered_at TEXT,
    FOREIGN KEY (seed_id) REFERENCES seeds(id)
);

CREATE INDEX IF NOT EXISTS idx_seeds_status ON seeds(status);
CREATE INDEX IF NOT EXISTS idx_seeds_type ON seeds(seed_type);
CREATE INDEX IF NOT EXISTS idx_questions_seed ON questions(seed_id);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
"""


def _datetime_to_str(dt: datetime | None) -> str | None:
    """Convert datetime to ISO format string."""
    if dt is None:
        return None
    return dt.isoformat()


def _str_to_datetime(s: str | None) -> datetime | None:
    """Convert ISO format string to datetime."""
    if s is None:
        return None
    return datetime.fromisoformat(s)


class Database:
    """SQLite database for seeds."""

    def __init__(self, path: Path | None = None):
        """Initialize database connection.

        Args:
            path: Path to database file. If None, uses .seeds/seeds.db in cwd.
        """
        if path is None:
            path = Path.cwd() / SEEDS_DIR / DB_FILE
        self.path = path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def init(self) -> None:
        """Initialize database schema and .seeds/.gitignore."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()

        # Create .gitignore inside .seeds/ (like beads' .beads/.gitignore)
        # Ignores SQLite DB and runtime files; JSONL is tracked by default.
        gitignore_path = self.path.parent / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(SEEDS_GITIGNORE)

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def is_initialized(self) -> bool:
        """Check if database exists and is initialized."""
        return self.path.exists()

    # --- Seed operations ---

    def _row_to_seed(self, row: sqlite3.Row) -> Seed:
        """Convert database row to Seed object."""
        return Seed(
            id=row["id"],
            title=row["title"],
            content=row["content"] or "",
            status=SeedStatus(row["status"]),
            seed_type=SeedType(row["seed_type"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            related_to=json.loads(row["related_to"]) if row["related_to"] else [],
            created_at=_str_to_datetime(row["created_at"]) or now_utc(),
            updated_at=_str_to_datetime(row["updated_at"]) or now_utc(),
            resolved_at=_str_to_datetime(row["resolved_at"]),
        )

    def create_seed(self, seed: Seed) -> Seed:
        """Insert a new seed into the database."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO seeds (id, title, content, status, seed_type, tags, related_to, created_at, updated_at, resolved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                seed.id,
                seed.title,
                seed.content,
                seed.status.value,
                seed.seed_type.value,
                json.dumps(seed.tags),
                json.dumps(seed.related_to),
                _datetime_to_str(seed.created_at),
                _datetime_to_str(seed.updated_at),
                _datetime_to_str(seed.resolved_at),
            ),
        )
        conn.commit()
        return seed

    def get_seed(self, seed_id: str) -> Seed | None:
        """Get a seed by ID."""
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM seeds WHERE id = ?", (seed_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_seed(row)

    def update_seed(self, seed: Seed) -> Seed:
        """Update an existing seed."""
        seed.updated_at = now_utc()
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE seeds SET
                title = ?, content = ?, status = ?, seed_type = ?,
                tags = ?, related_to = ?, updated_at = ?, resolved_at = ?
            WHERE id = ?
            """,
            (
                seed.title,
                seed.content,
                seed.status.value,
                seed.seed_type.value,
                json.dumps(seed.tags),
                json.dumps(seed.related_to),
                _datetime_to_str(seed.updated_at),
                _datetime_to_str(seed.resolved_at),
                seed.id,
            ),
        )
        conn.commit()
        return seed

    def delete_seed(self, seed_id: str) -> bool:
        """Delete a seed by ID. Returns True if deleted."""
        conn = self._get_conn()
        # Also delete associated questions
        conn.execute("DELETE FROM questions WHERE seed_id = ?", (seed_id,))
        result = conn.execute("DELETE FROM seeds WHERE id = ?", (seed_id,))
        conn.commit()
        return result.rowcount > 0

    def list_seeds(
        self,
        status: SeedStatus | None = None,
        seed_type: SeedType | None = None,
        tag: str | None = None,
        include_terminal: bool = False,
    ) -> list[Seed]:
        """List seeds with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM seeds WHERE 1=1"
        params: list = []

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)
        elif not include_terminal:
            # Exclude resolved and abandoned by default
            query += " AND status NOT IN (?, ?)"
            params.extend([SeedStatus.RESOLVED.value, SeedStatus.ABANDONED.value])

        if seed_type is not None:
            query += " AND seed_type = ?"
            params.append(seed_type.value)

        if tag is not None:
            # Search in JSON array
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_seed(row) for row in rows]

    def get_children(self, parent_id: str) -> list[Seed]:
        """Get direct children of a seed."""
        conn = self._get_conn()
        # Children have IDs like 'parent_id.N'
        pattern = f"{parent_id}.%"
        rows = conn.execute(
            """
            SELECT * FROM seeds
            WHERE id LIKE ? AND id NOT LIKE ?
            ORDER BY id
            """,
            (pattern, f"{parent_id}.%.%"),  # Exclude grandchildren
        ).fetchall()
        return [self._row_to_seed(row) for row in rows]

    def get_next_child_id(self, parent_id: str) -> str:
        """Generate the next child ID for a parent."""
        children = self.get_children(parent_id)
        if not children:
            return f"{parent_id}.1"

        # Find highest child number
        max_num = 0
        for child in children:
            suffix = child.id.split(".")[-1]
            try:
                num = int(suffix)
                max_num = max(max_num, num)
            except ValueError:
                pass

        return f"{parent_id}.{max_num + 1}"

    def is_blocked(self, seed_id: str) -> bool:
        """Check if a seed is blocked (has unresolved children)."""
        children = self.get_children(seed_id)
        for child in children:
            if not child.is_terminal():
                return True
        return False

    def get_blocked_seeds(self) -> list[Seed]:
        """Get all seeds that are blocked by unresolved children."""
        all_seeds = self.list_seeds(include_terminal=False)
        blocked = []
        for seed in all_seeds:
            if self.is_blocked(seed.id):
                blocked.append(seed)
        return blocked

    # --- Question operations ---

    def _row_to_question(self, row: sqlite3.Row) -> Question:
        """Convert database row to Question object."""
        return Question(
            id=row["id"],
            seed_id=row["seed_id"],
            text=row["text"],
            answer=row["answer"],
            status=QuestionStatus(row["status"]),
            created_at=_str_to_datetime(row["created_at"]) or now_utc(),
            answered_at=_str_to_datetime(row["answered_at"]),
        )

    def create_question(self, question: Question) -> Question:
        """Insert a new question into the database."""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO questions (id, seed_id, text, answer, status, created_at, answered_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                question.id,
                question.seed_id,
                question.text,
                question.answer,
                question.status.value,
                _datetime_to_str(question.created_at),
                _datetime_to_str(question.answered_at),
            ),
        )
        conn.commit()
        return question

    def get_question(self, question_id: str) -> Question | None:
        """Get a question by ID."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_question(row)

    def update_question(self, question: Question) -> Question:
        """Update an existing question."""
        conn = self._get_conn()
        conn.execute(
            """
            UPDATE questions SET
                text = ?, answer = ?, status = ?, answered_at = ?
            WHERE id = ?
            """,
            (
                question.text,
                question.answer,
                question.status.value,
                _datetime_to_str(question.answered_at),
                question.id,
            ),
        )
        conn.commit()
        return question

    def delete_question(self, question_id: str) -> bool:
        """Delete a question by ID. Returns True if deleted."""
        conn = self._get_conn()
        result = conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        conn.commit()
        return result.rowcount > 0

    def list_questions(
        self,
        seed_id: str | None = None,
        status: QuestionStatus | None = None,
    ) -> list[Question]:
        """List questions with optional filters."""
        conn = self._get_conn()
        query = "SELECT * FROM questions WHERE 1=1"
        params: list = []

        if seed_id is not None:
            query += " AND seed_id = ?"
            params.append(seed_id)

        if status is not None:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [self._row_to_question(row) for row in rows]

    def get_open_questions(self) -> list[Question]:
        """Get all open questions across all seeds."""
        return self.list_questions(status=QuestionStatus.OPEN)

    # --- Tag operations ---

    def get_all_tags(self) -> list[str]:
        """Get all unique tags used across seeds."""
        conn = self._get_conn()
        rows = conn.execute("SELECT tags FROM seeds").fetchall()
        all_tags: set[str] = set()
        for row in rows:
            if row["tags"]:
                tags = json.loads(row["tags"])
                all_tags.update(tags)
        return sorted(all_tags)
